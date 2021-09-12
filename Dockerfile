FROM python:3.9-slim

# Set pip to have cleaner logs and no saved cache
ENV PIP_NO_CACHE_DIR=false

# Update pip
RUN pip install -U pip

# Create the working directory
WORKDIR /modmail

# Copy requirements so they can be installed
COPY ./requirements.txt ./requirements.txt

# Install dependencies
RUN pip install -r ./requirements.txt


# Copy the source code in last to optimize rebuilding the image
COPY . .


CMD ["python", "-m", "modmail"]
