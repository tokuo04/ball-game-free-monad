const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
let ballState = { x: 400, y: 300, radius: 10 };

function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.beginPath();
    ctx.arc(ballState.x, ballState.y, ballState.radius, 0, Math.PI * 2);
    ctx.fillStyle = "#00FFCC";
    ctx.fill();
    ctx.closePath();
    requestAnimationFrame(render);
}
requestAnimationFrame(render);
