// recorder.js - Audio recording utilities using Web Audio API

/**
 * Class for handling audio recording functionality
 */
class AudioRecorder {
    constructor(options = {}) {
        this.options = Object.assign({
            mimeType: 'audio/webm',
            audioBitsPerSecond: 128000
        }, options);
        
        this.mediaRecorder = null;
        this.stream = null;
        this.chunks = [];
        this.isRecording = false;
        this.onDataAvailable = this.onDataAvailable.bind(this);
        this.onStop = this.onStop.bind(this);
        
        // Callbacks
        this.onStartCallback = null;
        this.onStopCallback = null;
        this.onDataCallback = null;
        this.onErrorCallback = null;
    }
    
    /**
     * Start recording audio
     */
    start() {
        if (this.isRecording) {
            return Promise.reject(new Error('Already recording'));
        }
        
        return navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                this.stream = stream;
                this.mediaRecorder = new MediaRecorder(stream, this.options);
                this.mediaRecorder.addEventListener('dataavailable', this.onDataAvailable);
                this.mediaRecorder.addEventListener('stop', this.onStop);
                this.mediaRecorder.start();
                this.isRecording = true;
                this.chunks = [];
                
                if (this.onStartCallback) {
                    this.onStartCallback(this.stream);
                }
                
                return stream;
            })
            .catch(error => {
                if (this.onErrorCallback) {
                    this.onErrorCallback(error);
                }
                return Promise.reject(error);
            });
    }
    
    /**
     * Stop recording audio
     */
    stop() {
        if (!this.isRecording) {
            return;
        }
        
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
        
        this.isRecording = false;
        
        // Stop all audio tracks
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
    }
    
    /**
     * Pause recording
     */
    pause() {
        if (this.isRecording && this.mediaRecorder && this.mediaRecorder.state === 'recording') {
            this.mediaRecorder.pause();
        }
    }
    
    /**
     * Resume recording
     */
    resume() {
        if (this.isRecording && this.mediaRecorder && this.mediaRecorder.state === 'paused') {
            this.mediaRecorder.resume();
        }
    }
    
    /**
     * Called when data is available from the recorder
     */
    onDataAvailable(e) {
        if (e.data.size > 0) {
            this.chunks.push(e.data);
        }
        
        if (this.onDataCallback) {
            this.onDataCallback(e.data);
        }
    }
    
    /**
     * Called when recording stops
     */
    onStop() {
        const audioBlob = new Blob(this.chunks, { type: this.options.mimeType });
        
        if (this.onStopCallback) {
            this.onStopCallback(audioBlob);
        }
    }
    
    /**
     * Register a callback for when recording starts
     */
    onStart(callback) {
        this.onStartCallback = callback;
    }
    
    /**
     * Register a callback for when recording stops
     */
    onStopRecording(callback) {
        this.onStopCallback = callback;
    }
    
    /**
     * Register a callback for when data is available
     */
    onData(callback) {
        this.onDataCallback = callback;
    }
    
    /**
     * Register a callback for when an error occurs
     */
    onError(callback) {
        this.onErrorCallback = callback;
    }
    
    /**
     * Check if browser supports required APIs
     */
    static isSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
    }
    
    /**
     * Create an audio element with the recording
     */
    createAudioElement(audioBlob) {
        const audioURL = URL.createObjectURL(audioBlob);
        const audio = document.createElement('audio');
        audio.src = audioURL;
        audio.controls = true;
        return audio;
    }
    
    /**
     * Convert blob to base64 for easier transfer
     */
    static blobToBase64(blob) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result);
            reader.onerror = reject;
            reader.readAsDataURL(blob);
        });
    }
}
