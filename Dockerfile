# TaskFlow ORIGINAL: Dockerfile propositalmente inseguro (didático)
FROM python:3.9
ARG SECRET_KEY=9f1c2e7a8b4d6e30a1b2c3d4e5f60718
ENV SECRET_KEY=$SECRET_KEY
ENV ADMIN_PASSWORD=Xk7Qp2vLe4Rz8Tn3Wm5Yb9
ENV FLASK_DEBUG=1
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "app.py"]
