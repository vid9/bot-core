# Instructions on how to install Rasa

### 1. Run
Download the install script on the server:
```bash
curl -sSL -o install.sh https://storage.googleapis.com/rasa-x-releases/0.40.1/install.sh
```

###2. Install
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
```bash
sudo apt update
```

###3. Download custom images
docker pull vid99/bot_action_server:latest

###4. Start up Rasa X and wait until all containers are running 
(-d will run Rasa X in the background):
```bash
cd /etc/rasa
sudo docker-compose up -d
```

### 5. Create file  docker-compose.override.yml
Paste inside:
```yaml
version:"3.4"
services:
  rasa-worker:
    volumes:
      - ./custom_component:/app/custom_component
    environment:
      PYTHONPATH: "${PYTHONPATH}:/app/custom_component"
  rasa-production:
    volumes:
      - ./custom_component:/app/custom_component
    environment:
      PYTHONPATH: "${PYTHONPATH}:/app/custom_component"
  app:
    image: vid99/bot_action_server:latest
    volumes:
      - ./classla_resources/:/classla_resources
```

###6. Define channel connectors
Additional channel connectors can be set in the **credentials.yml** file
https://rasa.com/docs/rasa/connectors/your-own-website

###7. Create password
`sudo python rasa_x_commands.py create --update admin me <PASSWORD>`
