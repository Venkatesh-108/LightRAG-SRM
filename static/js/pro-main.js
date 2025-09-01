// pro-main.js

document.addEventListener('DOMContentLoaded', () => {
    const converter = new showdown.Converter({ openLinksInNewWindow: true });
    const app = {
        // DOM Elements
        els: {
            navLinks: document.querySelectorAll('.sidebar-nav a'),
            chatInterface: document.querySelector('.chat-interface'),
            documentsPage: document.querySelector('.documents-page'),
            settingsPage: document.querySelector('.settings-page'),
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
            welcomeContent: document.querySelector('.welcome-content'),
            modelOptions: document.querySelectorAll('.model-option'),
            docChatHeader: document.getElementById('doc-chat-header'),
            docChatFilename: document.getElementById('doc-chat-filename'),
            exitDocChat: document.getElementById('exit-doc-chat'),
        },

        state: {
            activeDocument: null,
        },

        // API Communication
        api: {
            async getDocuments() {
                const response = await fetch('/documents');
                return response.json();
            },
            async sendQuery(query, filename = null) {
                const body = { query };
                if (filename) {
                    body.filename = filename;
                }
                const response = await fetch('/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });
                return response;
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
            async setModelProvider(provider) {
                const response = await fetch('/set_model', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider }),
                });
                return response.json();
            },
            async getCurrentModel() {
                const response = await fetch('/get_model');
                return response.json();
            },
        },

        // UI Management
        ui: {
            showDocChatHeader(filename) {
                app.els.docChatFilename.textContent = filename;
                app.els.docChatHeader.classList.add('active');
            },

            hideDocChatHeader() {
                app.els.docChatHeader.classList.remove('active');
                app.els.docChatFilename.textContent = '';
            },
            hideAllViews() {
                app.els.chatInterface.style.display = 'none';
                app.els.documentsPage.style.display = 'none';
                app.els.settingsPage.style.display = 'none';
            },

            switchView(view) {
                app.ui.hideAllViews();

                // Show selected section
                if (view === 'chat') {
                    app.els.chatInterface.style.display = 'flex';
                } else if (view === 'documents') {
                    app.els.documentsPage.style.display = 'block';
                    app.refreshDocuments();
                } else if (view === 'settings') {
                    if (app.els.settingsPage) {
                        app.els.settingsPage.style.display = 'block';
                        app.loadCurrentModel();
                    } else {
                        console.error('Settings page element not found');
                    }
                }
                
                // Update active link after switching
                app.els.navLinks.forEach(l => l.classList.remove('active'));
                const targetLink = document.querySelector(`.sidebar-nav a[data-view="${view}"]`);
                if (targetLink) targetLink.classList.add('active');
            },

            createMessageElement(text, type, query = '') {
                const messageElement = document.createElement('div');
                messageElement.classList.add('message', type, 'message-entry');

                const avatar = `<div class="avatar">${type === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>'}</div>`;
                
                let actions = '';
                if (type === 'bot') {
                    actions = `
                        <div class="message-actions">
                            <button class="action-btn copy-btn" title="Copy text"><i class="fas fa-copy"></i></button>
                            <button class="action-btn retry-btn" title="Retry" data-query="${query}"><i class="fas fa-sync-alt"></i></button>
                        </div>
                    `;
                }

                let formattedText;
                if (type === 'bot') {
                    formattedText = converter.makeHtml(text);
                } else {
                    const tempDiv = document.createElement('div');
                    tempDiv.textContent = text;
                    formattedText = tempDiv.innerHTML;
                }

                const messageContent = `
                    <div class="message-content">
                        <div class="text">${formattedText}</div>
                        ${actions}
                    </div>
                `;

                messageElement.innerHTML = avatar + messageContent;
                return messageElement;
            },
            createTypingIndicator() {
                return this.createMessageElement('<div class="typing-indicator"><span></span><span></span><span></span></div>', 'bot');
            },
            renderDocuments(documents) {
                app.els.documentsGrid.innerHTML = '';
                if (documents.length > 0) {
                    app.els.emptyState.style.display = 'none';
                    app.els.documentsGrid.style.display = 'flex'; // Use flex for a list

                    documents.forEach(doc => {
                        const item = document.createElement('div');
                        item.classList.add('document-item');

                        // Handle both old format (string) and new format (object)
                        const filename = typeof doc === 'string' ? doc : doc.filename;
                        const fileSize = typeof doc === 'object' ? doc.size : 0;
                        const pageCount = typeof doc === 'object' ? doc.pages : 0;

                        // Format file size
                        const formatFileSize = (bytes) => {
                            if (bytes === 0) return '0 B';
                            const k = 1024;
                            const sizes = ['B', 'KB', 'MB', 'GB'];
                            const i = Math.floor(Math.log(bytes) / Math.log(k));
                            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
                        };

                        const formattedSize = formatFileSize(fileSize);
                        const pageText = pageCount === 1 ? '1 page' : `${pageCount} pages`;

                        item.innerHTML = `
                            <div class="document-info">
                                <div class="file-icon"><i class="fas fa-file-pdf"></i></div>
                                <div class="file-details">
                                    <div class="document-name">${filename}</div>
                                    <div class="metadata">
                                        <span><i class="fas fa-hdd"></i> ${formattedSize}</span>
                                        <span><i class="fas fa-file-alt"></i> ${pageText}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="document-actions">
                                <button class="action-btn chat-doc-btn" data-filename="${filename}" title="Chat with document">
                                    <i class="fas fa-comments"></i>
                                </button>
                                <button class="action-btn delete" data-filename="${filename}" title="Delete document">
                                    <i class="fas fa-trash-alt"></i>
                                </button>
                            </div>
                        `;
                        app.els.documentsGrid.appendChild(item);
                    });
                } else {
                    app.els.documentsGrid.style.display = 'none';
                    app.els.emptyState.style.display = 'flex';
                }
            },
            showUploadModal(filename) {
                app.els.uploadFilename.textContent = filename;
                app.els.statusTitle.textContent = 'Uploading...';
                app.els.statusIcon.innerHTML = '<i class="fas fa-upload"></i>';
                app.els.statusIcon.className = 'status-icon';
                app.els.progressStage.textContent = 'Preparing upload...';
                app.els.indexingSteps.style.display = 'none';
                app.els.uploadModal.classList.add('active');
            },
            hideUploadModal() {
                setTimeout(() => {
                    app.els.uploadModal.classList.remove('active');
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
                    app.els.confirmationModal.classList.add('active');

                    const yesHandler = () => {
                        app.els.confirmationModal.classList.remove('active');
                        resolve(true);
                        cleanup();
                    };

                    const noHandler = () => {
                        app.els.confirmationModal.classList.remove('active');
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

                if (app.els.welcomeContent) {
                    app.els.welcomeContent.classList.add('hidden');
                }

                app.els.chatMessages.appendChild(app.ui.createMessageElement(messageText, 'user'));
                app.els.chatInput.value = '';
                app.els.chatMessages.scrollTop = app.els.chatMessages.scrollHeight;

                const typingIndicator = app.ui.createTypingIndicator();
                app.els.chatMessages.appendChild(typingIndicator);
                app.els.chatMessages.scrollTop = app.els.chatMessages.scrollHeight;

                let botMessageElement;
                let botTextElement;

                try {
                    const response = await app.api.sendQuery(messageText, app.state.activeDocument);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }

                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let fullResponse = '';
                    let firstChunk = true;

                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        if (firstChunk) {
                            typingIndicator.remove();
                            botMessageElement = app.ui.createMessageElement('', 'bot', messageText);
                            botTextElement = botMessageElement.querySelector('.text');
                            app.els.chatMessages.appendChild(botMessageElement);
                            firstChunk = false;
                        }

                        fullResponse += decoder.decode(value, { stream: true });
                        botTextElement.innerHTML = converter.makeHtml(fullResponse);
                        app.els.chatMessages.scrollTop = app.els.chatMessages.scrollHeight;
                    }

                } catch (error) {
                    if (typingIndicator) typingIndicator.remove();
                    if (!botMessageElement) {
                        botMessageElement = app.ui.createMessageElement('', 'bot', messageText);
                        botTextElement = botMessageElement.querySelector('.text');
                        app.els.chatMessages.appendChild(botMessageElement);
                    }
                    botTextElement.innerHTML = 'An error occurred. Please try again.';
                    botMessageElement.classList.add('error');
                } finally {
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
                        (status, responseText) => { // Completion
                            const endTime = Date.now();
                            const actualTime = ((endTime - startTime) / 1000).toFixed(1);

                            let response;
                            try {
                                response = JSON.parse(responseText);
                            } catch (e) {
                                response = { error: 'An unexpected error occurred.' };
                            }

                            if (status === 200) {
                                localStorage.setItem(`indexing-time-${file.name}`, actualTime);
                            }

                            setTimeout(() => {
                                app.ui.hideUploadModal();
                                if (status === 200) {
                                    const message = response.success || 'Document uploaded successfully!';
                                    app.ui.showToast(message, 'success');
                                    app.refreshDocuments();
                                } else if (status === 409) { // Duplicate file
                                    const message = response.error || 'This document already exists.';
                                    app.ui.showToast(message, 'warning');
                                } else { // Other errors
                                    const message = response.error || 'Upload failed. Please try again.';
                                    app.ui.showToast(message, 'error');
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
            handleMessageActions(event) {
                const copyBtn = event.target.closest('.copy-btn');
                if (copyBtn) {
                    const messageText = copyBtn.closest('.message-content').querySelector('.text').textContent;
                    navigator.clipboard.writeText(messageText).then(() => {
                        app.ui.showToast('Copied to clipboard!', 'success');
                    }).catch(err => {
                        app.ui.showToast('Failed to copy text.', 'error');
                    });
                    return;
                }

                const retryBtn = event.target.closest('.retry-btn');
                if (retryBtn) {
                    const query = retryBtn.dataset.query;
                    if (query) {
                        app.els.chatInput.value = query;
                        app.handlers.handleSendMessage();
                    }
                }
            },

            async handleModelSelection(event) {
                const selectedOption = event.currentTarget;
                const provider = selectedOption.dataset.provider;

                app.els.modelOptions.forEach(opt => opt.classList.remove('active'));
                selectedOption.classList.add('active');

                try {
                    const response = await fetch('/set_model', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ provider }),
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok && result.success) {
                        app.ui.showToast(`Model provider switched to ${provider}.`, 'success');
                    } else {
                        // Revert the selection if there was an error
                        app.els.modelOptions.forEach(opt => opt.classList.remove('active'));
                        const currentProvider = await app.api.getCurrentModel();
                        const currentOption = document.querySelector(`[data-provider="${currentProvider.provider}"]`);
                        if (currentOption) {
                            currentOption.classList.add('active');
                        }
                        
                        const errorMsg = result.error || 'Failed to switch model.';
                        app.ui.showToast(errorMsg, 'error');
                    }
                } catch (error) {
                    // Revert the selection if there was an error
                    app.els.modelOptions.forEach(opt => opt.classList.remove('active'));
                    const currentProvider = await app.api.getCurrentModel();
                    const currentOption = document.querySelector(`[data-provider="${currentProvider.provider}"]`);
                    if (currentOption) {
                        currentOption.classList.add('active');
                    }
                    
                    app.ui.showToast('An error occurred while switching models.', 'error');
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
            handleOpenDocument(event) {
                const docNameElement = event.target.closest('.document-name');
                if (docNameElement) {
                    const docName = docNameElement.textContent;
                    window.open(`/documents/${docName}`, '_blank');
                }
            },

            handleChatWithDocument(event) {
                const chatBtn = event.target.closest('.chat-doc-btn');
                if (!chatBtn) return;

                const filename = chatBtn.dataset.filename;
                app.state.activeDocument = filename;

                // Clear chat history and show welcome screen
                app.els.chatMessages.innerHTML = '';
                if (app.els.welcomeContent) {
                    app.els.welcomeContent.classList.remove('hidden');
                }
                
                app.ui.showDocChatHeader(filename);
                app.ui.switchView('chat');
                app.els.chatInput.focus();
                app.els.chatInput.placeholder = `Ask a question about ${filename}...`;
                app.ui.showToast(`Switched to chat with ${filename}`, 'info');
            },
            handleRefreshDocuments(event) {
                const refreshButton = app.els.refreshDocs;
                const refreshIcon = refreshButton.querySelector('i');
                refreshIcon.classList.add('refreshing-icon');
                setTimeout(() => refreshIcon.classList.remove('refreshing-icon'), 1000);
                app.refreshDocuments();
            },
        },

        async refreshDocuments() {
            const documents = await app.api.getDocuments();
            app.ui.renderDocuments(documents);
        },

        async loadCurrentModel() {
            try {
                const result = await app.api.getCurrentModel();
                if (result.provider) {
                    app.els.modelOptions.forEach(opt => opt.classList.remove('active'));
                    const activeOption = document.querySelector(`[data-provider="${result.provider}"]`);
                    if (activeOption) {
                        activeOption.classList.add('active');
                    }
                }
            } catch (error) {
                console.log('Could not load current model provider');
            }
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
                const view = e.currentTarget.dataset.view;
                if (view === 'chat') {
                    window.location.href = '/';
                } else {
                    app.ui.switchView(view);
                }
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
                app.els.refreshDocs.addEventListener('click', this.handlers.handleRefreshDocuments);
            }
            if (app.els.modalClose) {
                app.els.modalClose.addEventListener('click', () => app.ui.hideUploadModal());
            }
            if (app.els.documentsGrid) {
                app.els.documentsGrid.addEventListener('click', (e) => {
                    this.handlers.handleDeleteDocument(e);
                    this.handlers.handleOpenDocument(e);
                    this.handlers.handleChatWithDocument(e);
                });
            }
            if (app.els.exitDocChat) {
                app.els.exitDocChat.addEventListener('click', () => {
                    app.state.activeDocument = null;
                    app.ui.hideDocChatHeader();
                    app.els.chatInput.placeholder = 'Send a message...';
                    app.ui.showToast('Exited document chat.', 'info');
                });
            }
            app.els.chatMessages.addEventListener('click', this.handlers.handleMessageActions);
            app.els.modelOptions.forEach(option => option.addEventListener('click', this.handlers.handleModelSelection));

            // Initial state
            const initialView = document.body.dataset.initialView || 'chat';
            console.log('Initial view:', initialView); // Debug log
            app.ui.switchView(initialView);
            app.animations.animateSuggestionCards(); // Animate cards on load
        },
    };

    app.init();
});
