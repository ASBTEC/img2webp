# img2webp
Converts images into webp format

## Quick start (Python)
No Docker required.

### Create virtual environment
```shell
python3 -m venv venv
```

### Install dependencies
```shell
venv/bin/pip install -r requirements.txt
```

### Run
```shell
venv/bin/python src/main.py --input-location ./input --output-location ./output
```

Add `--verbose` for detailed logging.

---

## Setup (Docker)
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

### Build software
```shell
docker build . -t aleixmt/img2webp:latest
```

### Install alias
```shell
echo "
alias img2webp=\"docker run --rm -it --user \"\$(id -u):\$(id -g)\" -v \"$PWD/input:/data/in:ro\" -v \"$PWD/output:/data/out\" aleixmt/img2webp:latest --input-location /data/in --output-location /data/out --verbose\"" >> $HOME/.bashrc
source $HOME/.bashrc
```


## Usage
Each time you want to convert images.
### Put the images in the `input` folder
```shell
mv your/photo/location/photo.png output/
```

### Run software
```shell
img2webp
```

### Get images
Your images are in the `output` folder. 