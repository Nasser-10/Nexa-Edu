/* Interactive HTML5 Canvas Calm Educational Wave Physics Animation */
(function() {
    const canvas = document.getElementById('waveCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let width = canvas.width = canvas.parentElement.offsetWidth;
    let height = canvas.height = 140;

    window.addEventListener('resize', () => {
        if (!canvas.parentElement) return;
        width = canvas.width = canvas.parentElement.offsetWidth;
        height = canvas.height = 140;
    });

    let step = 0;
    
    // Wave configurations: calm teal, emerald, soft navy transparent layers
    const waves = [
        { amplitude: 18, frequency: 0.012, speed: 0.025, color: 'rgba(20, 184, 166, 0.35)' }, // Teal 500
        { amplitude: 24, frequency: 0.008, speed: 0.018, color: 'rgba(13, 148, 136, 0.45)' }, // Teal 600
        { amplitude: 14, frequency: 0.015, speed: 0.035, color: 'rgba(16, 185, 129, 0.25)' } // Emerald 500
    ];

    // Floating light particles
    const particles = Array.from({ length: 25 }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        radius: Math.random() * 2 + 1,
        speedY: Math.random() * 0.4 + 0.1,
        opacity: Math.random() * 0.5 + 0.2
    }));

    function render() {
        ctx.clearRect(0, 0, width, height);
        step += 1;

        // Render Wave Layers
        waves.forEach((wave, idx) => {
            ctx.beginPath();
            ctx.moveTo(0, height);

            for (let x = 0; x <= width; x += 10) {
                const y = Math.sin(x * wave.frequency + step * wave.speed) * wave.amplitude + (height - 45 + idx * 8);
                ctx.lineTo(x, y);
            }

            ctx.lineTo(width, height);
            ctx.closePath();
            ctx.fillStyle = wave.color;
            ctx.fill();
        });

        // Render ambient particles
        particles.forEach(p => {
            p.y -= p.speedY;
            if (p.y < 0) {
                p.y = height;
                p.x = Math.random() * width;
            }
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${p.opacity})`;
            ctx.fill();
        });

        requestAnimationFrame(render);
    }

    render();
})();
