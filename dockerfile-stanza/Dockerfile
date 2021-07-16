FROM rasa/rasa:2.7.1-full

# Switch to root user
USER root

# Do other stuff, e.g.: add python dependencies, etc.
RUN pip install stanza

# Switch back to a non-root user
USER 1001
