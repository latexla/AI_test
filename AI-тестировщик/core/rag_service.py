# core/rag_service.py
import os
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.faiss import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain.chat_models.gigachat import GigaChat
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.schema import Document
from pdf2image import convert_from_path
import pytesseract
import easyocr
import logging

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGService:
    def __init__(
        self,
        auth_token: str,
        model_name: str = "GigaChat",
        embedding_model: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        chunk_size: int = 500,
        chunk_overlap: int = 100
    ):
        """
        Инициализация RAG-сервиса
        
        :param auth_token: Токен авторизации GigaChat
        :param model_name: Название модели GigaChat
        :param embedding_model: Модель для эмбеддингов
        :param chunk_size: Размер чанков при разделении текста
        :param chunk_overlap: Перекрытие чанков
        """
        self.auth_token = auth_token
        self.model_name = model_name
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.llm = None
        self.retrieval_chain = None
        self.vector_store = None
        
        self._initialize_components()

    def _initialize_components(self):
        """Инициализация основных компонентов"""
        self.llm = GigaChat(
            credentials=self.auth_token,
            model=self.model_name,
            verify_ssl_certs=False,
            profanity_check=False
        )
        
        # Инициализация модели для эмбеддингов
        self.embedding = HuggingFaceEmbeddings(
            model_name=self.embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': False}
        )

    def load_and_process_documents(self, pdf_paths: List[str]) -> None:
        """
        Загрузка и обработка PDF-документов
        
        :param pdf_paths: Список путей к PDF-файлам
        """
        all_docs = []
        
        for pdf_path in pdf_paths:
            try:
                logger.info(f"Обработка файла: {pdf_path}")
                docs = self._load_pdf(pdf_path)
                all_docs.extend(docs)
            except Exception as e:
                logger.error(f"Ошибка при обработке файла {pdf_path}: {str(e)}")
                continue
        
        if not all_docs:
            raise ValueError("Не удалось загрузить ни одного документа")
        
        self._create_vector_store(all_docs)

    def _load_pdf(self, pdf_path: str) -> List[Document]:
        """Загрузка PDF с fallback на OCR при необходимости"""
        try:
            # Попытка загрузки текста напрямую
            loader = PyPDFLoader(pdf_path)
            docs = loader.load()
            
            if docs and any(doc.page_content.strip() for doc in docs):
                return docs
            
            # Fallback на OCR
            logger.info("Текст не извлечен. Используем OCR...")
            text = self._extract_text_with_ocr(pdf_path)
            return [Document(page_content=text)]
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке PDF: {str(e)}")
            raise

    def _extract_text_with_ocr(self, pdf_path: str, max_pages: int = 87) -> str:
        """Извлечение текста из PDF с помощью OCR"""
        text = ""
        images = convert_from_path(pdf_path, dpi=100)
        
        for i, image in enumerate(images[:max_pages]):
            try:
                logger.info(f"Обработка страницы {i + 1}...")
                page_text = pytesseract.image_to_string(image, lang='eng')
                text += page_text
            except Exception as e:
                logger.warning(f"Ошибка OCR на странице {i + 1}: {str(e)}")
                continue
                
        return text

    def _create_vector_store(self, documents: List[Document]) -> None:
        """Создание векторного хранилища"""
        try:
            # Разделение на чанки
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
            split_docs = text_splitter.split_documents(documents)
            
            logger.info(f"Создается векторное хранилище из {len(split_docs)} чанков")
            
            # Создание FAISS индекса
            self.vector_store = FAISS.from_documents(
                split_docs,
                embedding=self.embedding
            )
            
            # Инициализация цепочки
            self._setup_retrieval_chain()
            
        except Exception as e:
            logger.error(f"Ошибка при создании векторного хранилища: {str(e)}")
            raise

    def _setup_retrieval_chain(self) -> None:
        """Настройка RAG-цепочки"""
        prompt_template = '''Напиши код максимально развернуто на вопрос пользователя. \
Используй при этом только информацию из контекста. Если в контексте нет \
информации для ответа, сообщи об этом пользователю и скажи что есть похожего в запросе.
Контекст: {context}
Вопрос: {input}
Ответ:'''
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        document_chain = create_stuff_documents_chain(
            llm=self.llm,
            prompt=prompt
        )
        
        retriever = self.vector_store.as_retriever(search_kwargs={"k": 5})
        self.retrieval_chain = create_retrieval_chain(retriever, document_chain)

    def query(self, question: str) -> dict:
        """
        Выполнение запроса к RAG-системе
        
        :param question: Вопрос пользователя
        :return: Ответ системы с контекстом
        """
        if not self.retrieval_chain:
            raise ValueError("Векторное хранилище не инициализировано. Сначала загрузите документы.")
            
        try:
            response = self.retrieval_chain.invoke({'input': question})
            logger.info(f"Успешно обработан запрос: '{question}'")
            return {
                "answer": response.get("answer", ""),
                "context": response.get("context", [])
            }
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса '{question}': {str(e)}")
            raise