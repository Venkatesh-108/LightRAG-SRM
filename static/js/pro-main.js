// pro-main.js

document.addEventListener('DOMContentLoaded', () => {
    const app = {
        // DOM Elements
        els: {
            navLinks: document.querySelectorAll('.sidebar-nav a'),
            chatInterface: document.querySelector('.chat-interface'),
            documentsPage: document.querySelector('.documents-page'),
            sendButton: document.querySelector('.send-button'),
            chatInput: document.querySelector('.chat-input'),
            chatMessages: document.querySelector('.chat-messages'),
            uploadButton: document.querySelector('.upload-button'),
            uploadButtonSecondary: document.querySelector('.upload-button-secondary'),
            fileInput: document.getElementById('file-input'),
            documentsGrid: document.getElementById('documents-grid'),
            emptyState: document.getElementById('empty-state'),
            refreshDocs: document.getElementById('refresh-docs'),
            uploadModal: document.getElementById('upload-modal'),
            uploadFilename: document.getElementById('upload-filename'),
            progressBar: document.getElementById('progress-bar'),
            uploadProgressText: document.getElementById('upload-progress-text'),
            progressStage: document.getElementById('progress-stage'),
            statusIcon: document.getElementById('status-icon'),
            statusTitle: document.getElementById('status-title'),
            indexingSteps: document.getElementById('indexing-steps'),
            modalClose: document.getElementById('modal-close'),
            deleteAllButton: document.querySelector('.delete-all-button'),
            toastContainer: document.getElementById('toast-container'),
            confirmationModal: document.getElementById('confirmation-modal'),
            confirmationMessage: document.getElementById('confirmation-message'),
            confirmYes: document.getElementById('confirm-yes'),
            confirmNo: document.getElementById('confirm-no'),
            suggestionCards: document.querySelectorAll('.suggestion-card'),
        },

        // API Communication
        api: {
            async getDocuments() {
                const response = await fetch('/documents');
                return response.json();
            },
            async sendQuery(query) {
                const response = await fetch('/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query }),
                });
                return response.json();
            },
            uploadFile(file, progressCallback, completionCallback) {
                const formData = new FormData();
                formData.append('file', file);
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/upload', true);

                xhr.upload.onprogress = progressCallback;
                xhr.onload = () => completionCallback(xhr.status, xhr.responseText);
                xhr.onerror = () => completionCallback(0, 'Network error');
                xhr.send(formData);
            },
            async deleteDocument(filename) {
                const response = await fetch(`/delete/${filename}`, { method: 'DELETE' });
                return response.json();
            },
            async deleteAllDocuments() {
                const response = await fetch('/delete_all', { method: 'DELETE' });
                return response.json();
            },
        },

        // UI Management
        ui: {
            switchView(view) {
                app.els.navLinks.forEach(l => l.classList.remove('active'));
                const targetLink = document.querySelector(`.sidebar-nav a[data-view="${view}"]`);
                if (targetLink) targetLink.classList.add('active');

                // Hide all sections
                app.els.chatInterface.style.display = 'none';
                app.els.documentsPage.style.display = 'none';

                // Show selected section
                if (view === 'chat') {
                    app.els.chatInterface.style.display = 'flex';
                } else if (view === 'documents') {
                    app.els.documentsPage.style.display = 'block';
                    app.refreshDocuments();
                }
            },
            createMessageElement(text, type) {
                const messageElement = document.createElement('div');
                messageElement.classList.add('message', type);
                const icon = `<div class="icon">${type === 'user' ? 'U' : 'AI'}</div>`;
                const textDiv = `<div class="text">${text}</div>`;
                messageElement.innerHTML = type === 'user' ? textDiv + icon : icon + textDiv;
                return messageElement;
            },
            createTypingIndicator() {
                return this.createMessageElement('<div class="typing-indicator"><span></span><span></span><span></span></div>', 'bot');
            },
            renderDocuments(documents) {
                if (documents.length > 0) {
                    app.els.documentsGrid.innerHTML = '';
                    app.els.emptyState.style.display = 'none';
                    
                    documents.forEach(doc => {
                        const docItem = document.createElement('div');
                        docItem.classList.add('document-item');
                        
                        // Get actual indexing time from storage or default
                        const indexingTime = localStorage.getItem(`indexing-time-${doc}`) || '~5.0';
                        
                        docItem.innerHTML = `
                            <div class="document-icon">
                                <i class="fas fa-file-pdf"></i>
                            </div>
                            <div class="document-info">
                                <div class="document-name">${doc}</div>
                                <div class="document-meta">
                                    <span><i class="fas fa-calendar"></i> Added today</span>
                                    <span><i class="fas fa-check-circle"></i> Indexed in ${indexingTime}s</span>
                                </div>
                            </div>
                            <div class="document-actions">
                                <button class="action-btn" title="Chat about this document">
                                    <i class="fas fa-comments"></i>
                                </button>
                                <button class="action-btn delete" data-filename="${doc}" title="Delete document">
                                    <i class="fas fa-trash-alt"></i>
                                </button>
                            </div>
                        `;
                        app.els.documentsGrid.appendChild(docItem);
                    });
                } else {
                    app.els.documentsGrid.innerHTML = '';
                    app.els.emptyState.style.display = 'block';
                }
            },
            showUploadModal(filename) {
                app.els.uploadFilename.textContent = filename;
                app.els.statusTitle.textContent = 'Uploading...';
                app.els.statusIcon.innerHTML = '<i class="fas fa-upload"></i>';
                app.els.statusIcon.className = 'status-icon';
                app.els.progressStage.textContent = 'Preparing upload...';
                app.els.indexingSteps.style.display = 'none';
                app.els.uploadModal.style.display = 'flex';
            },
            hideUploadModal() {
                setTimeout(() => {
                    app.els.uploadModal.style.display = 'none';
                    this.resetUploadModal();
                }, 500);
            },
            updateUploadProgress(percent) {
                app.els.progressBar.style.width = percent + '%';
                app.els.uploadProgressText.textContent = Math.round(percent) + '%';
                
                if (percent < 100) {
                    app.els.progressStage.textContent = 'Uploading file...';
                } else {
                    app.els.progressStage.textContent = 'Processing document...';
                    app.startIndexingAnimation();
                }
            },
            resetUploadModal() {
                this.updateUploadProgress(0);
                app.els.uploadFilename.textContent = '';
                app.els.fileInput.value = '';
                app.els.indexingSteps.style.display = 'none';
                app.els.statusIcon.className = 'status-icon';
                // Reset all steps
                document.querySelectorAll('.step').forEach(step => {
                    step.classList.remove('active', 'completed');
                });
            },
            showToast(message, type = 'info') {
                const toast = document.createElement('div');
                toast.classList.add('toast', type);
                toast.textContent = message;
                app.els.toastContainer.appendChild(toast);
                setTimeout(() => toast.remove(), 5000);
            },
            showConfirmation(message) {
                return new Promise((resolve) => {
                    app.els.confirmationMessage.textContent = message;
                    app.els.confirmationModal.style.display = 'flex';

                    const yesHandler = () => {
                        app.els.confirmationModal.style.display = 'none';
                        resolve(true);
                        cleanup();
                    };

                    const noHandler = () => {
                        app.els.confirmationModal.style.display = 'none';
                        resolve(false);
                        cleanup();
                    };

                    const cleanup = () => {
                        app.els.confirmYes.removeEventListener('click', yesHandler);
                        app.els.confirmNo.removeEventListener('click', noHandler);
                    };

                    app.els.confirmYes.addEventListener('click', yesHandler);
                    app.els.confirmNo.addEventListener('click', noHandler);
                });
            },
            
            startIndexingAnimation() {
                app.els.statusTitle.textContent = 'Processing Document';
                app.els.statusIcon.innerHTML = '<i class="fas fa-cog"></i>';
                app.els.statusIcon.className = 'status-icon processing';
                app.els.indexingSteps.style.display = 'block';
                
                const steps = ['step-extract', 'step-chunk', 'step-embed', 'step-index'];
                let currentStep = 0;
                
                const processStep = () => {
                    if (currentStep > 0) {
                        document.getElementById(steps[currentStep - 1]).classList.remove('active');
                        document.getElementById(steps[currentStep - 1]).classList.add('completed');
                    }
                    
                    if (currentStep < steps.length) {
                        document.getElementById(steps[currentStep]).classList.add('active');
                        currentStep++;
                        setTimeout(processStep, 1500);
                    } else {
                        // All steps completed
                        setTimeout(() => {
                            app.els.statusTitle.textContent = 'Document Ready!';
                            app.els.statusIcon.innerHTML = '<i class="fas fa-check"></i>';
                            app.els.statusIcon.className = 'status-icon success';
                            app.els.progressStage.textContent = 'Document successfully indexed';
                        }, 500);
                    }
                };
                
                setTimeout(processStep, 500);
            },
        },

        // Event Handlers
        handlers: {
            async handleSendMessage() {
                const messageText = app.els.chatInput.value.trim();
                if (!messageText) return;

                app.els.chatMessages.appendChild(app.ui.createMessageElement(messageText, 'user'));
                app.els.chatInput.value = '';
                app.els.chatMessages.scrollTop = app.els.chatMessages.scrollHeight;

                const typingIndicator = app.ui.createTypingIndicator();
                app.els.chatMessages.appendChild(typingIndicator);
                app.els.chatMessages.scrollTop = app.els.chatMessages.scrollHeight;

                try {
                    const data = await app.api.sendQuery(messageText);
                    const message = app.ui.createMessageElement(data.response || data.error, 'bot');
                    if (data.error) message.classList.add('error');
                    app.els.chatMessages.appendChild(message);
                } catch (error) {
                    const errorMsg = app.ui.createMessageElement('An error occurred. Please try again.', 'bot');
                    errorMsg.classList.add('error');
                    app.els.chatMessages.appendChild(errorMsg);
                } finally {
                    typingIndicator.remove();
                    app.els.chatMessages.scrollTop = app.els.chatMessages.scrollHeight;
                }
            },
            handleFileUpload(event) {
                const files = event.target.files;
                if (!files || files.length === 0) return;

                // Handle multiple files
                Array.from(files).forEach(file => {
                    const startTime = Date.now();
                    app.ui.showUploadModal(file.name);

                    app.api.uploadFile(file, 
                        (e) => { // Progress
                            if (e.lengthComputable) {
                                app.ui.updateUploadProgress((e.loaded / e.total) * 100);
                            }
                        },
                        (status, response) => { // Completion
                            const endTime = Date.now();
                            const actualTime = ((endTime - startTime) / 1000).toFixed(1);
                            
                            // Store the actual indexing time
                            if (status === 200) {
                                localStorage.setItem(`indexing-time-${file.name}`, actualTime);
                            }
                            
                            setTimeout(() => {
                                app.ui.hideUploadModal();
                                if (status === 200) {
                                    // Extract success message with timing from response
                                    const message = response.success || 'Document uploaded and indexed successfully!';
                                    app.ui.showToast(message, 'success');
                                    app.refreshDocuments();
                                } else {
                                    app.ui.showToast('Upload failed. Please try again.', 'error');
                                }
                            }, 2000); // Show completion state for 2 seconds
                        }
                    );
                });
            },
            async handleDeleteDocument(event) {
                const deleteBtn = event.target.closest('.action-btn.delete');
                if (!deleteBtn) return;
                
                const filename = deleteBtn.dataset.filename;
                const confirmed = await app.ui.showConfirmation(`Are you sure you want to delete ${filename}?`);
                
                if (confirmed) {
                    const result = await app.api.deleteDocument(filename);
                    if (result.success) {
                        app.ui.showToast('Document deleted successfully.', 'success');
                        app.refreshDocuments();
                    } else {
                        app.ui.showToast(result.error || 'Failed to delete document.', 'error');
                    }
                }
            },
            async handleDeleteAllDocuments() {
                const confirmed = await app.ui.showConfirmation('Are you sure you want to delete ALL documents? This action cannot be undone.');
                if (confirmed) {
                    const result = await app.api.deleteAllDocuments();
                    if (result.success) {
                        app.ui.showToast('All documents have been deleted.', 'success');
                        app.refreshDocuments();
                    } else {
                        app.ui.showToast(result.error || 'Failed to delete all documents.', 'error');
                    }
                }
            },
        },

        async refreshDocuments() {
            const documents = await app.api.getDocuments();
            app.ui.renderDocuments(documents);
        },

        // UI Animations
        animations: {
            animateSuggestionCards() {
                app.els.suggestionCards.forEach((card, index) => {
                    card.style.animationDelay = `${index * 100}ms`;
                });
            },
        },

        // Initialization
        async init() {
            // Setup event listeners
            app.els.navLinks.forEach(link => link.addEventListener('click', (e) => {
                e.preventDefault();
                app.ui.switchView(e.currentTarget.dataset.view);
            }));
            app.els.sendButton.addEventListener('click', this.handlers.handleSendMessage);
            app.els.chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handlers.handleSendMessage();
                }
            });
            app.els.uploadButton.addEventListener('click', () => app.els.fileInput.click());
            if (app.els.uploadButtonSecondary) {
                app.els.uploadButtonSecondary.addEventListener('click', () => app.els.fileInput.click());
            }
            app.els.fileInput.addEventListener('change', this.handlers.handleFileUpload);
            app.els.deleteAllButton.addEventListener('click', this.handlers.handleDeleteAllDocuments);
            if (app.els.refreshDocs) {
                app.els.refreshDocs.addEventListener('click', () => app.refreshDocuments());
            }
            if (app.els.modalClose) {
                app.els.modalClose.addEventListener('click', () => app.ui.hideUploadModal());
            }
            if (app.els.documentsGrid) {
                app.els.documentsGrid.addEventListener('click', this.handlers.handleDeleteDocument);
            }

            // Initial state
            app.ui.switchView('chat');
            app.animations.animateSuggestionCards(); // Animate cards on load
            const documents = await this.api.getDocuments();
            this.ui.renderDocuments(documents);
        },
    };

    app.init();
});
