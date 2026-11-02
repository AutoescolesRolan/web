function initPad(canvasId) {
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext('2d');
    let drawing = false;
    let hasContent = false;

    function resize() {
        const ratio = Math.max(window.devicePixelRatio || 1, 1);
        const rect = canvas.getBoundingClientRect();
        const w = Math.round(rect.width * ratio), h = Math.round(rect.height * ratio);
        if (w === canvas.width && h === canvas.height) return;   // res a fer: no esborrem la signatura
        // canviar la mida d'un canvas l'esborra: en guardem el contingut i el tornem a pintar
        let copia = null;
        if (hasContent && canvas.width && canvas.height) {
            copia = document.createElement('canvas');
            copia.width = canvas.width; copia.height = canvas.height;
            copia.getContext('2d').drawImage(canvas, 0, 0);
        }
        canvas.width = w;
        canvas.height = h;
        if (copia) ctx.drawImage(copia, 0, 0, copia.width, copia.height, 0, 0, w, h);
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.scale(ratio, ratio);
        ctx.lineWidth = 2.2;
        ctx.lineCap = 'round';
        ctx.strokeStyle = '#1e293b';
    }
    resize();
    window.addEventListener('resize', resize);

    function getPos(e) {
        const rect = canvas.getBoundingClientRect();
        if (e.touches && e.touches.length > 0) {
            return { x: e.touches[0].clientX - rect.left, y: e.touches[0].clientY - rect.top };
        }
        return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }

    function start(e) {
        e.preventDefault();
        drawing = true;
        hasContent = true;
        const pos = getPos(e);
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
    }

    function move(e) {
        if (!drawing) return;
        e.preventDefault();
        const pos = getPos(e);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
    }

    function end(e) {
        drawing = false;
    }

    canvas.addEventListener('mousedown', start);
    canvas.addEventListener('mousemove', move);
    window.addEventListener('mouseup', end);

    canvas.addEventListener('touchstart', start, { passive: false });
    canvas.addEventListener('touchmove', move, { passive: false });
    canvas.addEventListener('touchend', end);

    return {
        clear: function () {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            hasContent = false;
        },
        isEmpty: function () {
            return !hasContent;
        },
        toDataURL: function () {
            return canvas.toDataURL('image/png');
        }
    };
}
