FROM astral/uv:python3.13-trixie-slim

# System dependency needed by lightgbm
RUN apt-get -y update && \
    apt-get install -y libgomp1

# Install project dependencies
COPY pyproject.toml .
RUN uv sync

COPY main.py .
COPY src ./src
CMD ["uv", "run", "main.py"]
