// main.js - Main application JavaScript

let isInitialized = false; // Flag to ensure single initialization

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize home page UI behavior
    initializeHomePage();
    
    // Initialize recording functionality if on home page and not already initialized
    if (document.getElementById('recordButton') && !isInitialized) {
        initializeRecording();
        isInitialized = true; // Set flag after successful initialization
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

// Global visualization functions
function setupVisualization(stream, recordingVisualizerContainer, isRecordingRef) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(stream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    
    canvas = document.createElement('canvas');
    canvas.width = recordingVisualizerContainer.clientWidth || 300;
    canvas.height = 60;
    recordingVisualizerContainer.innerHTML = '';
    recordingVisualizerContainer.appendChild(canvas);
    canvasCtx = canvas.getContext('2d');
    
    visualize(isRecordingRef);
}

function visualize(isRecordingRef) {
    if (!analyser) return;
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    function draw() {
        if (!isRecordingRef.value) return;
        
        requestAnimationFrame(draw);
        
        analyser.getByteFrequencyData(dataArray);
        
        canvasCtx.fillStyle = 'rgb(30, 30, 30)';
        canvasCtx.fillRect(0, 0, canvas.width, canvas.height);
        
        const barWidth = (canvas.width / bufferLength) * 1.5;
        const barSpacing = 2;
        let x = 0;
        
        for (let i = 0; i < bufferLength; i++) {
            const rawHeight = dataArray[i];
            const barHeight = (rawHeight / 255) * (canvas.height - 10);
            const alpha = Math.min(1, rawHeight / 120);
            canvasCtx.fillStyle = `rgb(156, 39, 176, ${alpha})`;
            canvasCtx.fillRect(x, canvas.height - barHeight, barWidth - barSpacing, barHeight);
            x += barWidth + barSpacing;
        }
    }
    
    draw();
}

function initializeRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('getUserMedia not supported in this browser');
        showAlert('Audio recording is not supported in your browser. Please try a modern browser like Chrome, Firefox, or Edge.', 'warning');
        return;
    }
    const recordButton = document.getElementById('recordButton');
    const stopRecordButton = document.getElementById('stopRecordButton');
    const recordStatus = document.getElementById('recordStatus');
    const recordingVisualizerContainer = document.getElementById('recordingVisualizer');
    const titleInput = document.getElementById('recordingTitle');
    const submitButton = document.getElementById('submit');
    const recordForm = document.getElementById('recordForm');

    let recorder;
    let audioChunks = [];
    let isRecording = false;
    let audioContext;
    let analyser;
    let canvas;
    let canvasCtx;
    let recordedBlob = null;

    function getMp3MediaRecorderOptions() {
        const options = {};
        if (MediaRecorder.isTypeSupported('audio/mp3')) {
            options.mimeType = 'audio/mp3';
        } else if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
            options.mimeType = 'audio/webm;codecs=opus';
        } else {
            console.warn('Neither MP3 nor WebM supported. Falling back to default format.');
        }
        return options;
    }

    function startRecording() {
        const constraints = {
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
        };
        
        recordStatus.textContent = 'Requesting microphone access...';
        
        navigator.mediaDevices.getUserMedia(constraints)
            .then(stream => {
                console.log("Microphone access granted");
                recorder = new MediaRecorder(stream, getMp3MediaRecorderOptions());
                console.log("MediaRecorder initialized with MIME type:", recorder.mimeType);
                
                if (!recordingVisualizerContainer) {
                    console.error('recordingVisualizerContainer not found in DOM');
                    showAlert('Visualization container not found. Please check the HTML.', 'danger');
                    return;
                }
                
                const isRecordingRef = { value: true };
                setupVisualization(stream, recordingVisualizerContainer, isRecordingRef);
                
                recorder.ondataavailable = e => {
                    if (e.data.size > 0) audioChunks.push(e.data); // Only push non-empty chunks
                };
                recorder.onstop = () => {
                    isRecordingRef.value = false;
                    recordedBlob = new Blob(audioChunks, { type: recorder.mimeType || 'audio/wav' });
                    console.log("Recording stopped, blob created with type:", recordedBlob.type, "size:", recordedBlob.size, "duration (approx):", recordedBlob.size / 128000 * 8, "seconds");
                    stopRecordButton.classList.add('d-none');
                    submitButton.disabled = false;
                    recordStatus.textContent = 'Recording stopped. Click Transcribe to submit.';
                    recordStatus.classList.remove('text-primary');
                    recordStatus.classList.add('text-success');
                    // Stop all tracks to release microphone
                    stream.getTracks().forEach(track => track.stop());
                };
                
                audioChunks = [];
                recorder.start(250); // Reduced to 250ms chunks for better boundary detection
                isRecording = true;
                
                recordButton.classList.add('d-none');
                stopRecordButton.classList.remove('d-none');
                recordStatus.textContent = 'Recording... (click stop when finished)';
                recordStatus.classList.remove('text-secondary');
                recordStatus.classList.add('text-primary');
                recordingVisualizerContainer.classList.remove('d-none');
            })
            .catch(error => {
                console.error('Error accessing microphone:', error);
                let errorMessage = 'Error accessing microphone. ';
                if (error.name === 'NotAllowedError') errorMessage += 'You denied permission.';
                else if (error.name === 'NotFoundError') errorMessage += 'No microphone detected.';
                else if (error.name === 'NotReadableError') errorMessage += 'Microphone in use.';
                else errorMessage += error.message;
                showAlert(errorMessage, 'danger');
            });
    }
    
    function stopRecording() {
        if (recorder && isRecording) {
            recorder.stop();
            isRecording = false;
        }
    }

    let isSubmitting = false;
    let requestId = 0;

    // Remove existing listener before adding new one
    const existingSubmitListener = recordForm._submitListener;
    if (existingSubmitListener) {
        recordForm.removeEventListener('submit', existingSubmitListener);
    }

    recordForm.addEventListener('submit', function(event) {
        console.log('Submit listener triggered');
        if (isSubmitting) {
            console.warn('Duplicate submission prevented');
            event.preventDefault();
            return;
        }

        event.preventDefault();
        const formData = new FormData(this);
        const submitButton = document.getElementById('submit');
        const recordStatus = document.getElementById('recordStatus');
        const historyContainer = document.querySelector('.transcription-history-sidebar');

        if (!recordedBlob) {
            showAlert('No recording to submit. Please record audio first.', 'danger');
            return;
        }

        isSubmitting = true;
        submitButton.disabled = true;
        recordForm.querySelectorAll('button').forEach(btn => btn.disabled = true);
        const currentRequestId = ++requestId;
        const title = titleInput ? titleInput.value.trim() || 'Voice Recording' : 'Voice Recording';
        formData.append('audio', recordedBlob, `recording.${recordedBlob.type.split('/')[1] || 'wav'}`);
        formData.append('title', title);
        formData.append('request_id', currentRequestId);

        console.log('Submitting audio:', {
            blobSize: recordedBlob.size,
            blobType: recordedBlob.type,
            sentAs: `recording.${recordedBlob.type.split('/')[1] || 'wav'}`,
            requestId: currentRequestId,
            title: title
        });

        recordStatus.textContent = 'Processing...';
        recordStatus.classList.remove('text-success');
        recordStatus.classList.add('text-warning');

        let attempt = 0;
        const maxAttempts = 1;
        function makeRequest() {
            fetch('/transcribe_recording', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    return response.text().then(text => {
                        throw new Error(text || `Server error: ${response.status} ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('Server response:', data);
                if (data.success) {
                    if (historyContainer) {
                        const now = new Date().toLocaleString('en-US', { month: 'long', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true });
                        const item = document.createElement('div');
                        item.className = 'transcription-item';
                        item.setAttribute('data-id', data.id);
                        item.innerHTML = `<h6 class="mb-1">${title}</h6><div class="transcription-date"><small>${now}</small></div>`;
                        if (historyContainer.firstChild) {
                            historyContainer.insertBefore(item, historyContainer.firstChild);
                        } else {
                            historyContainer.appendChild(item);
                        }
                        console.log('History updated with ID:', data.id, 'Title:', title);
                    }
                    window.transcriptionData = null;
                    setTimeout(() => {
                        window.location.href = `/view_transcription/${data.id}`;
                        recordedBlob = null;
                        recordForm.reset();
                        const resultCards = document.getElementById('resultCards');
                        if (resultCards) resultCards.classList.add('d-none');
                    }, 100);
                } else {
                    throw new Error(data.error || 'Unknown server error');
                }
            })
            .catch(error => {
                console.error('Error details:', error);
                attempt++;
                if (attempt < maxAttempts && error.message.includes('NetworkError')) {
                    console.log(`Retry attempt ${attempt} of ${maxAttempts}`);
                    setTimeout(makeRequest, 1000);
                } else {
                    submitButton.disabled = false;
                    recordStatus.textContent = 'Processing failed. Try again.';
                    recordStatus.classList.remove('text-warning');
                    recordStatus.classList.add('text-danger');
                    recordForm.querySelectorAll('button').forEach(btn => btn.disabled = false);
                    if (!(error.message.includes('NetworkError') && document.location.pathname === '/view_transcription/')) {
                        showAlert('Error submitting recording: ' + error.message, 'danger');
                    }
                    isSubmitting = false;
                }
            })
            .finally(() => {
                isSubmitting = false;
                if (attempt >= maxAttempts) {
                    recordForm.querySelectorAll('button').forEach(btn => btn.disabled = false);
                }
            });
        }
        makeRequest();
    });
    recordForm._submitListener = arguments.callee; // Store the listener for removal

    if (recordButton) recordButton.addEventListener('click', startRecording);
    if (stopRecordButton) stopRecordButton.addEventListener('click', stopRecording);
}

// ... (rest of the file remains unchanged)
// Initialize file upload functionality
function initializeFileUpload() {
    const fileInput = document.getElementById('audioFileInput');
    const fileLabel = document.getElementById('audioFileLabel');
    const titleInput = document.getElementById('title');
    
    if (fileInput && fileLabel) {
        fileInput.addEventListener('change', function() {
            if (fileInput.files.length > 0) {
                const fileName = fileInput.files[0].name;
                fileLabel.textContent = fileName;
                fileLabel.style.color = "white";
                if (titleInput && !titleInput.value) {
                    const baseName = fileName.split('.').slice(0, -1).join('.');
                    titleInput.value = baseName || fileName;
                }
            } else {
                fileLabel.textContent = 'Choose audio file';
                fileLabel.style.color = "var(--text-muted)";
            }
        });
    }
}

function initializeTranscriptionList() {
    const transcriptionItems = document.querySelectorAll('.transcription-item');
    transcriptionItems.forEach(item => {
        item.addEventListener('click', function() {
            const transcriptionId = this.getAttribute('data-id');
            if (transcriptionId) window.location.href = `/view_transcription/${transcriptionId}`;
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
    alertElement.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>`;
    alertsContainer.appendChild(alertElement);
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
    
    if (showRecordButton) showRecordButton.addEventListener('click', function() {
        initialButtonsContainer.classList.add('d-none');
        recordPanel.classList.remove('d-none');
    });
    if (showUploadButton) showUploadButton.addEventListener('click', function() {
        initialButtonsContainer.classList.add('d-none');
        uploadPanel.classList.remove('d-none');
    });
    if (backFromRecordButton) backFromRecordButton.addEventListener('click', function() {
        recordPanel.classList.add('d-none');
        initialButtonsContainer.classList.remove('d-none');
    });
    if (backFromUploadButton) backFromUploadButton.addEventListener('click', function() {
        uploadPanel.classList.add('d-none');
        initialButtonsContainer.classList.remove('d-none');
    });
}