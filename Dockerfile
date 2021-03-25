#ARG RASA_SDK_VERSION
# Extend the official Rasa SDK image
#FROM rasa/rasa-sdk:${RASA_SDK_VERSION}
FROM rasa/rasa-sdk:2.4.1

# Use subdirectory as working directory
WORKDIR /app

# Change back to root user to install dependencies
USER root

# To install system dependencies
RUN apt-get update -qq && \
    apt-get install -y curl jq && \
    apt-get -y install locales && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN sed -i '/sl_SI.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen
ENV LANG sl_SI.UTF-8
ENV LANGUAGE sl_SI:sl
ENV LC_ALL sl_SI.UTF-8
ENV TZ="Europe/Ljubljana"

# To install packages from PyPI
COPY  ./tmp/requirements.txt /tmp/requirements.txt
RUN pip install pip install torch==1.4.0+cpu torchvision==0.5.0+cpu -f https://download.pytorch.org/whl/torch_stable.html
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy actions folder to working directory
COPY ./tmp/actions /app/actions

# Switch back to non-root to run code
USER 1001

