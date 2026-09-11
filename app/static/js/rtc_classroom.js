/* Interactive Live Classroom Real-Time Signaling & Whiteboard Engine */
class LiveClassroomManager {
    constructor(roomCode, userName, isTeacher = false) {
        this.roomCode = roomCode;
        this.userName = userName;
        this.isTeacher = isTeacher;
        this.socket = null;
        this.isDrawing = false;
        this.currentColor = '#0d9488';
        this.brushSize = 3;
        this.canvas = null;
        this.ctx = null;
    }

    initWebSocket(onMessageCallback) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/v1/live/ws/${this.roomCode}`;
        
        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log(`Connected to Live Classroom WebSocket: ${this.roomCode}`);
            this.sendSignal({
                type: 'USER_JOINED',
                user_name: this.userName,
                is_teacher: this.isTeacher
            });
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'WHITEBOARD_DRAW') {
                    this.handleRemoteDraw(data);
                } else if (data.type === 'WHITEBOARD_CLEAR') {
                    if (this.ctx && this.canvas) {
                        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
                    }
                }
                if (onMessageCallback) onMessageCallback(data);
            } catch (e) {
                console.error("Malformed WebSocket payload", e);
            }
        };

        this.socket.onclose = () => {
            console.log("Classroom WebSocket disconnected.");
        };
    }

    sendSignal(payload) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify(payload));
        }
    }

    sendChatMessage(text) {
        this.sendSignal({
            type: 'CHAT_MESSAGE',
            user_name: this.userName,
            text: text,
            timestamp: new Date().toLocaleTimeString()
        });
    }

    sendRaiseHand() {
        this.sendSignal({
            type: 'RAISE_HAND',
            user_name: this.userName,
            message: `✋ ${this.userName} قام برفع اليد لطرح سؤال`
        });
    }

    initWhiteboard(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        
        this.canvas.width = this.canvas.parentElement.offsetWidth || 700;
        this.canvas.height = 380;

        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        let lastX = 0;
        let lastY = 0;

        const getPos = (e) => {
            const rect = this.canvas.getBoundingClientRect();
            return {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
        };

        this.canvas.onmousedown = (e) => {
            this.isDrawing = true;
            const pos = getPos(e);
            lastX = pos.x;
            lastY = pos.y;
        };

        this.canvas.onmousemove = (e) => {
            if (!this.isDrawing) return;
            const pos = getPos(e);
            
            this.drawSegment(lastX, lastY, pos.x, pos.y, this.currentColor, this.brushSize);
            
            // Broadcast drawing line to participants
            this.sendSignal({
                type: 'WHITEBOARD_DRAW',
                x1: lastX,
                y1: lastY,
                x2: pos.x,
                y2: pos.y,
                color: this.currentColor,
                size: this.brushSize
            });

            lastX = pos.x;
            lastY = pos.y;
        };

        this.canvas.onmouseup = () => this.isDrawing = false;
        this.canvas.onmouseleave = () => this.isDrawing = false;
    }

    drawSegment(x1, y1, x2, y2, color, size) {
        if (!this.ctx) return;
        this.ctx.beginPath();
        this.ctx.strokeStyle = color;
        this.ctx.lineWidth = size;
        this.ctx.moveTo(x1, y1);
        this.ctx.lineTo(x2, y2);
        this.ctx.stroke();
    }

    handleRemoteDraw(data) {
        this.drawSegment(data.x1, data.y1, data.x2, data.y2, data.color, data.size);
    }

    clearWhiteboard() {
        if (this.ctx && this.canvas) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            this.sendSignal({ type: 'WHITEBOARD_CLEAR' });
        }
    }
}
