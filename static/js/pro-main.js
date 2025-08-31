// pro-main.js

document.addEventListener('DOMContentLoaded', () => {
    const app = {
        // DOM Elements
        els: {
            navLinks: document.querySelectorAll('.sidebar-nav a'),
            chatInterface: document.querySelector('.chat-interface'),
            documentLibrary: document.querySelector('.document-library'),
            sendButton: document.querySelector('.send-button'),
            chatInput: document.querySelector('.chat-input'),
            chatMessages: document.querySelector('.chat-messages'),
            uploadButton: document.querySelector('.upload-button'),
            fileInput: document.getElementById('file-input'),
            documentGrid: document.querySelector('.document-grid'),
            uploadModal: document.getElementById('upload-modal'),
            uploadFilename: document.getElementById('upload-filename'),
            progressBar: document.getElementById('progress-bar'),
            uploadProgressText: document.getElementById('upload-progress-text'),
            deleteAllButton: document.querySelector('.delete-all-button'),
            toastContainer: document.getElementById('toast-container'),
            confirmationModal: document.getElementById('confirmation-modal'),
            confirmationMessage: document.getElementById('confirmation-message'),
            confirmYes: document.getElementById('confirm-yes'),
            confirmNo: document.getElementById('confirm-no'),
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
                document.querySelector(`.sidebar-nav a[data-view="${view}"]`).classList.add('active');

                if (view === 'chat') {
                    app.els.chatInterface.style.display = 'flex';
                    app.els.documentLibrary.style.display = 'none';
                } else {
                    app.els.chatInterface.style.display = 'none';
                    app.els.documentLibrary.style.display = 'block';
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
                app.els.documentGrid.innerHTML = '';
                if (documents.length > 0) {
                    documents.forEach(doc => {
                        const docCard = document.createElement('div');
                        docCard.classList.add('document-card');
                        docCard.innerHTML = `
                            <h3>${doc}</h3>
                            <p>PDF Document</p>
                            <div class="document-card-actions">
                                <button class="delete-doc-button" data-filename="${doc}"><i class="fas fa-trash-alt"></i> Delete</button>
                            </div>
                        `;
                        app.els.documentGrid.appendChild(docCard);
                    });
                } else {
                    app.els.documentGrid.innerHTML = '<p>No documents found. Upload a document to get started.</p>';
                }
            },
            showUploadModal(filename) {
                app.els.uploadFilename.textContent = filename;
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
            },
            resetUploadModal() {
                this.updateUploadProgress(0);
                app.els.uploadFilename.textContent = '';
                app.els.fileInput.value = '';
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
                const file = event.target.files[0];
                if (!file) return;

                app.ui.showUploadModal(file.name);

                app.api.uploadFile(file, 
                    (e) => { // Progress
                        if (e.lengthComputable) {
                            app.ui.updateUploadProgress((e.loaded / e.total) * 100);
                        }
                    },
                    (status, response) => { // Completion
                        app.ui.hideUploadModal();
                        if (status === 200) {
                            app.ui.showToast('File uploaded successfully!', 'success');
                            app.refreshDocuments();
                        } else {
                            app.ui.showToast('Upload failed. Please try again.', 'error');
                        }
                    }
                );
            },
            async handleDeleteDocument(event) {
                if (!event.target.closest('.delete-doc-button')) return;
                const button = event.target.closest('.delete-doc-button');
                const filename = button.dataset.filename;
                
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
            app.els.fileInput.addEventListener('change', this.handlers.handleFileUpload);
            app.els.deleteAllButton.addEventListener('click', this.handlers.handleDeleteAllDocuments);
            app.els.documentGrid.addEventListener('click', this.handlers.handleDeleteDocument);

            // Initial state
            app.ui.switchView('chat');
            const documents = await this.api.getDocuments();
            this.ui.renderDocuments(documents);
        },
    };

    app.init();
});
