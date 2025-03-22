// main.js - Main application JavaScript

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize recording functionality if on home page
    if (document.getElementById('recordButton')) {
        initializeRecording();
    }
    
    // Initialize file upload preview
    initializeFileUpload();
    
    // Handle transcription list items
    initializeTranscriptionList();
});

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
}

// Initialize recording functionality
function initializeRecording() {
    const recordButton = document.getElementById('recordButton');
    const stopRecordButton = document.getElementById('stopRecordButton');
    const recordStatus = document.getElementById('recordStatus');
    const recordingControls = document.getElementById('recordingControls');
    const recordingVisualizerContainer = document.getElementById('recordingVisualizer');
    const titleInput = document.getElementById('recordingTitle');
    const processingOverlay = document.getElementById('processingOverlay');
    
    let recorder;
    let audioChunks = [];
    let isRecording = false;
    let audioContext;
    let analyser;
    let canvas;
    let canvasCtx;
    
    // Set up recording visualization
    function setupVisualization(stream) {
        // Create audio context and analyser
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(stream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);
        
        // Create canvas for visualization
        canvas = document.createElement('canvas');
        canvas.width = recordingVisualizerContainer.clientWidth;
        canvas.height = 60;
        recordingVisualizerContainer.innerHTML = '';
        recordingVisualizerContainer.appendChild(canvas);
        canvasCtx = canvas.getContext('2d');
        
        // Start visualization
        visualize();
    }
    
    // Handle visualization drawing
    function visualize() {
        if (!analyser) return;
        
        const bufferLength = analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        function draw() {
            if (!isRecording) return;
            
            requestAnimationFrame(draw);
            
            analyser.getByteFrequencyData(dataArray);
            
            canvasCtx.fillStyle = 'rgb(26, 26, 46)';
            canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
            
            const barWidth = (canvas.width / bufferLength) * 2.5;
            let barHeight;
            let x = 0;
            
            for (let i = 0; i < bufferLength; i++) {
                barHeight = dataArray[i] / 2;
                
                // Use primary color for bars
                canvasCtx.fillStyle = `rgb(142, 68, 173)`;
                canvasCtx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                
                x += barWidth + 1;
            }
        }
        
        draw();
    }
    
    // Start recording function
    function startRecording() {
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                recorder = new MediaRecorder(stream);
                
                // Set up recording visualization
                setupVisualization(stream);
                
                recorder.ondataavailable = e => {
                    audioChunks.push(e.data);
                };
                
                recorder.onstop = () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    submitRecording(audioBlob);
                };
                
                audioChunks = [];
                recorder.start();
                isRecording = true;
                
                // Update UI
                recordButton.classList.add('d-none');
                stopRecordButton.classList.remove('d-none');
                recordStatus.textContent = 'Recording... (click stop when finished)';
                recordStatus.classList.remove('text-secondary');
                recordStatus.classList.add('text-danger');
                recordingVisualizerContainer.classList.remove('d-none');
            })
            .catch(error => {
                console.error('Error accessing microphone:', error);
                showAlert('Error accessing microphone. Please check your browser permissions.', 'danger');
            });
    }
    
    // Stop recording function
    function stopRecording() {
        if (recorder && isRecording) {
            recorder.stop();
            isRecording = false;
            
            // Update UI
            stopRecordButton.classList.add('d-none');
            recordButton.classList.remove('d-none');
            recordStatus.textContent = 'Processing audio...';
            recordStatus.classList.remove('text-danger');
            recordStatus.classList.add('text-warning');
            processingOverlay.classList.remove('d-none');
        }
    }
    
    // Submit recording to the server for transcription
    function submitRecording(audioBlob) {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        formData.append('title', titleInput.value || 'Voice Recording');
        
        fetch('/transcribe_recording', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Reload the page to show the new transcription
                window.location.reload();
            } else {
                showAlert(data.error || 'Failed to transcribe audio.', 'danger');
                processingOverlay.classList.add('d-none');
                recordStatus.textContent = 'Ready to record';
                recordStatus.classList.remove('text-warning');
                recordStatus.classList.add('text-secondary');
            }
        })
        .catch(error => {
            console.error('Error submitting recording:', error);
            showAlert('Error submitting recording. Please try again.', 'danger');
            processingOverlay.classList.add('d-none');
            recordStatus.textContent = 'Ready to record';
            recordStatus.classList.remove('text-warning');
            recordStatus.classList.add('text-secondary');
        });
    }
    
    // Attach event listeners
    if (recordButton) {
        recordButton.addEventListener('click', startRecording);
    }
    
    if (stopRecordButton) {
        stopRecordButton.addEventListener('click', stopRecording);
    }
}

// Initialize file upload functionality
function initializeFileUpload() {
    const fileInput = document.getElementById('audioFileInput');
    const fileLabel = document.getElementById('audioFileLabel');
    
    if (fileInput && fileLabel) {
        fileInput.addEventListener('change', function() {
            if (fileInput.files.length > 0) {
                const fileName = fileInput.files[0].name;
                fileLabel.textContent = fileName;
            } else {
                fileLabel.textContent = 'Choose audio file';
            }
        });
    }
}

// Initialize transcription list click handlers
function initializeTranscriptionList() {
    const transcriptionItems = document.querySelectorAll('.transcription-item');
    
    transcriptionItems.forEach(item => {
        item.addEventListener('click', function() {
            const transcriptionId = this.getAttribute('data-id');
            if (transcriptionId) {
                window.location.href = `/transcription/${transcriptionId}`;
            }
        });
    });
}

// Helper function to show alerts
function showAlert(message, type = 'info') {
    const alertsContainer = document.getElementById('alertsContainer');
    
    if (!alertsContainer) {
        console.error('Alerts container not found');
        return;
    }
    
    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${type} alert-dismissible fade show`;
    alertElement.role = 'alert';
    alertElement.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertsContainer.appendChild(alertElement);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alertElement);
        bsAlert.close();
    }, 5000);
}
