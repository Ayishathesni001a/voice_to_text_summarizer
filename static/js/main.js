// main.js - Main application JavaScript

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize home page UI behavior
    initializeHomePage();
    
    // Initialize recording functionality if on home page
    if (document.getElementById('recordButton')) {
        initializeRecording();
    }
    
    // Initialize file upload preview
    initializeFileUpload();
    
    // Handle transcription list items
    initializeTranscriptionList();
    
    // Hide result cards initially - they should only show after processing
    const resultCards = document.getElementById('resultCards');
    if (resultCards) {
        resultCards.classList.add('d-none');
    }
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
            
            canvasCtx.fillStyle = 'rgb(30, 30, 30)';
            canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
            
            const barWidth = (canvas.width / bufferLength) * 2.5;
            let barHeight;
            let x = 0;
            
            for (let i = 0; i < bufferLength; i++) {
                barHeight = dataArray[i] / 2;
                
                // Use primary color for bars with gradient effect based on height
                const intensity = Math.min(255, Math.floor(barHeight * 3));
                canvasCtx.fillStyle = `rgb(156, 39, 176, ${barHeight/60})`;
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
                // Hide processing overlay
                processingOverlay.classList.add('d-none');
                
                // Display the results
                const resultCards = document.getElementById('resultCards');
                const transcriptionResult = document.getElementById('transcriptionResult');
                const summaryResult = document.getElementById('summaryResult');
                const editBtn = document.getElementById('editTranscriptionBtn');
                const downloadBtn = document.getElementById('downloadPdfBtn');
                
                if (resultCards && transcriptionResult && summaryResult) {
                    // Show the results container
                    resultCards.classList.remove('d-none');
                    
                    // Display transcription
                    transcriptionResult.textContent = data.transcription || 'No transcription available';
                    
                    // Display summary if available
                    if (data.summary) {
                        summaryResult.textContent = data.summary;
                    } else {
                        summaryResult.textContent = 'Summary not available';
                    }
                    
                    // Set up buttons
                    if (editBtn && data.id) {
                        editBtn.addEventListener('click', function() {
                            window.location.href = `/transcription/${data.id}/edit`;
                        });
                    }
                    
                    if (downloadBtn && data.id) {
                        downloadBtn.addEventListener('click', function() {
                            window.location.href = `/transcription/${data.id}/pdf`;
                        });
                    }
                    
                    // Update status
                    recordStatus.textContent = 'Transcription complete';
                    recordStatus.classList.remove('text-warning');
                    recordStatus.classList.add('text-success');
                    
                    // Scroll to results
                    resultCards.scrollIntoView({ behavior: 'smooth' });
                } else {
                    // Fallback if the result containers aren't found
                    window.location.href = `/transcription/${data.id}`;
                }
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

// Initialize home page UI behavior
function initializeHomePage() {
    const showRecordButton = document.getElementById('showRecordButton');
    const showUploadButton = document.getElementById('showUploadButton');
    const recordPanel = document.getElementById('recordPanel');
    const uploadPanel = document.getElementById('uploadPanel');
    const backFromRecordButton = document.getElementById('backFromRecord');
    const backFromUploadButton = document.getElementById('backFromUpload');
    const initialButtonsContainer = document.querySelector('.justify-content-center.gap-4');
    
    // Show Record Panel
    if (showRecordButton) {
        showRecordButton.addEventListener('click', function() {
            initialButtonsContainer.classList.add('d-none');
            recordPanel.classList.remove('d-none');
        });
    }
    
    // Show Upload Panel
    if (showUploadButton) {
        showUploadButton.addEventListener('click', function() {
            initialButtonsContainer.classList.add('d-none');
            uploadPanel.classList.remove('d-none');
        });
    }
    
    // Back from Record Panel
    if (backFromRecordButton) {
        backFromRecordButton.addEventListener('click', function() {
            recordPanel.classList.add('d-none');
            initialButtonsContainer.classList.remove('d-none');
        });
    }
    
    // Back from Upload Panel
    if (backFromUploadButton) {
        backFromUploadButton.addEventListener('click', function() {
            uploadPanel.classList.add('d-none');
            initialButtonsContainer.classList.remove('d-none');
        });
    }
}
