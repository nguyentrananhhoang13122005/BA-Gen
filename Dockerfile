FROM python:3.11-slim

WORKDIR /app

# Cài đặt các công cụ hệ thống cần thiết
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Sao chép và cài đặt các thư viện phụ thuộc
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép toàn bộ mã nguồn vào container
COPY . .

# Mở cổng Streamlit mặc định
EXPOSE 8501

# Thiết lập biến môi trường
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Khởi chạy ứng dụng Web
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
