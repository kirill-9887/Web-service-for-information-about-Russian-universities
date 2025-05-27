function addVideoBackground() {
    const videoDiv = document.createElement('div');
    videoDiv.className = 'video-background';

    const video = document.createElement('video');
    video.id = 'video';
    video.setAttribute('autoplay', '');
    video.setAttribute('muted', '');
    video.setAttribute('loop', '');

    const source = document.createElement('source');
    source.src = '/background-video.mp4';
    source.type = 'video/mp4';

    const fallbackText = document.createTextNode('Ваш браузер не поддерживает видео.');

    video.appendChild(source);
    video.appendChild(fallbackText);
    videoDiv.appendChild(video);

    document.body.insertBefore(videoDiv, document.body.firstChild);
}

document.addEventListener('DOMContentLoaded', addVideoBackground);