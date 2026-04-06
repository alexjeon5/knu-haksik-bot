FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필수 파일 복사 및 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# 실행
CMD ["python", "main.py"]