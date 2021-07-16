# Instructions on how to install Rasa

## 1. Run
Download the install script on the server:
```bash
curl -sSL -o install.sh https://storage.googleapis.com/rasa-x-releases/0.41.1/install.sh
```

## 2. Install
To install all of the files into the default folder, /etc/rasa, run:
```bash
sudo bash ./install.sh
```

###### If this error occurs: 
*E: Conflicting values set for option Signed-By regarding source https://download.docker.com/linux/ubuntu/ focal: /usr/share/keyrings/docker-archive-keyring.gpg != 
E: The list of sources could not be read.*

###### Remove the file: 
```bash
sudo rm /etc/apt/sources.list.d/docker.list
```

###### Run
If the error is fixed, do step 2 again.
```bash
sudo apt update
sudo bash ./install.sh
```

## 3. Download model resources 
###USING CLASSLA
Install classla
```bash
python3 -m pip install classla
```
Open python console, import classla and download all the slovenian models in "/etc/rasa/classla_resources/".
```bash
python3
import classla
classla.download("sl", "/etc/rasa/classla_resources/")
```

###USING STANZA
Install stanza
```bash
python3 -m pip install stanza
```
Open python console, import stanza and download all the slovenian models in "/etc/rasa/stanza_resources/".
```bash
python3
import stanza
stanza.download("sl", "/etc/rasa/stanza_resources/")
```

## Build docker image
Classla: 
```bash
sudo docker build -t rasa-classla:1.0 .
```
Stanza: 
```bash
sudo docker build -t rasa-stanza:1.0 .
```

## 5. Edit file  docker-compose.yml
Change x-rasa-services image in docker-compose.yml from image: "rasa/rasa:${RASA_VERSION}"
```yaml
x-rasa-services: &default-rasa-service
  restart: always
  image: "rasa/rasa:${RASA_VERSION}"
```
to "vid99/rasa-classla".
```yaml
x-rasa-services: &default-rasa-service
  restart: always
  image: "rasa-classla:1.0"
```

## 6. Create file  docker-compose.override.yml
```yaml
version: '3.4'
services:
  rasa-worker:
    volumes:
      - ./custom_component:/app/custom_component
      - ./classla_resources:/app/classla_resources
    environment:
      PYTHONPATH: "${PYTHONPATH}:/app/custom_component"
  rasa-production:
    volumes:
      - ./custom_component:/app/custom_component
      - ./classla_resources:/app/classla_resources
    environment:
      PYTHONPATH: "${PYTHONPATH}:/app/custom_component"
  app:
    image: vid99/bot_action_server:latest
    volumes:
      - ./classla_resources/:/classla_resources
```

## 6. Create folder custom_component and create files classla_tokenizer.py and stanza_tokenizer.py

## 7. Start up Rasa X and wait until all containers are downloaded and running 
(-d will run Rasa X in the background):
```bash
cd /etc/rasa
sudo docker-compose up -d
```

## 8. Create password
`sudo python rasa_x_commands.py create --update admin me <PASSWORD>`

Visit hostname in a browser and login into rasa X.

### 9. Add Rasa ssh key to the git repository and train a model.

### . Define channel connectors
Additional channel connectors can be set in the **credentials.yml** file
https://rasa.com/docs/rasa/connectors/your-own-website
