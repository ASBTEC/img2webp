# img2webp
Converts images into webp format

## Setup
Once for machine.
### Install git
```shell
sudo apt install -y git
```

### Clone repo
```shell
git clone https://github.com/ASBTEC/img2webp
```

### Install Docker
```shell
cd img2webp
sudo bash tools/install_docker.sh
```


## Usage
Each time you want to convert images.
### Put the images in the `input` folder
```shell
mv your/photo/location/photo.png output/
```

### Run software
```shell
docker compose up --build
```

### Get images
Your images are in the `output` folder. 