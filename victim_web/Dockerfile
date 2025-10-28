FROM python:3.11-slim
WORKDIR /app
COPY app.py /app/
COPY log_forwarder.py ../
RUN pip install flask requests
EXPOSE 80
CMD ["python", "app.py"]
