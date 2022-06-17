FROM nvidia/cuda:10.0-runtime-ubuntu18.04

ARG USER_NAME=blenderproc
ARG USER_ID=999
ARG GROUP_NAME=blenderproc
ARG GROUP_ID=999

WORKDIR /synthetic_data

ENV DEBIAN_FRONTEND=noninteractive
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV HW=GPU
ENV PATH=/home/${USER_NAME}/.local/bin:$PATH

RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    git \
    libfontconfig1 \
    libfreeimage-dev \
    libgl1 \
    libjpeg-dev \
    libxi-dev \
    libxrender1 \
    libxxf86vm1 \
    python3-pip \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 \
    && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

COPY ["resources/bop_data","/synthetic_data/resources/bop_data/"]
COPY ["resources/specprep_models","/synthetic_data/resources/specprep_models/"]
COPY ["resources/camera_positions","/synthetic_data/resources/camera_positions"]
COPY ["bop_physics_rendering.py","download_cc_textures.py","/synthetic_data/"]

RUN groupadd -g ${GROUP_ID} ${USER_NAME} \
    && useradd -r -u ${USER_ID} -g ${GROUP_NAME} -m -s /bin/bash ${USER_NAME} \
    && chown -R ${USER_NAME}:${GROUP_NAME} /synthetic_data

USER ${USER_NAME}
ENV USER=${USER_NAME}

RUN pip install blenderproc

# Importing blenderproc will download the correct blender dependencies
RUN echo 'import blenderproc' > blenderproc-dry-run.py \
    && blenderproc run blenderproc-dry-run.py \
    && rm blenderproc-dry-run.py

# Will download all required cc_textures
RUN blenderproc run download_cc_textures.py /synthetic_data/resources/cc_textures/

ENTRYPOINT ["blenderproc","run","bop_physics_rendering.py"]