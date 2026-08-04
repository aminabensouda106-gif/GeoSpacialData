FROM python:3.11-slim #image de base

WORKDIR /app #repertoire de travail du container

COPY requirements.txt . #copier le fichier requirements.txt dans le container
RUN pip install --no-cache-dir -r requirements.txt #installer les les paquets /biblio de python

COPY gee_export.py run_loop.sh ./ #copier le programme d export NDV et celui de la boucle de relance dans /app/
RUN chmod +x run_loop.sh #pour rendre le script executable 

CMD ["./run_loop.sh"] #automatisation du lancement lors de demarage du contenuer
