FROM python:3.12-slim

WORKDIR /trabajo

COPY sistema-inscripciones/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY sistema-inscripciones/app ./sistema-inscripciones/app
COPY evaluacion/corregir.py ./evaluacion/corregir.py

RUN useradd --create-home --uid 1000 evaluador
USER evaluador

ENTRYPOINT ["python", "evaluacion/corregir.py"]
CMD ["/agente"]
