FROM python:3.12.10-slim-bookworm
WORKDIR /app
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY clearpath ./clearpath
COPY public ./public
COPY fixtures ./fixtures
RUN useradd --uid 10001 --create-home clearpath && chown -R clearpath:clearpath /app
USER clearpath
ENV CLEARPATH_MODE=aws
EXPOSE 4181
CMD ["gunicorn", "--bind", "0.0.0.0:4181", "--workers", "1", "--threads", "2", "--timeout", "90", "clearpath.web:app"]
