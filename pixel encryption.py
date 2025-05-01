import sys
import os
import numpy as np
from PIL import Image
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, 
                            QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, 
                            QComboBox, QSlider, QSpinBox, QLineEdit, QMessageBox,
                            QGroupBox, QFormLayout, QTabWidget, QProgressBar,
                            QRadioButton, QButtonGroup, QSplitter, QFrame,
                            QToolTip, QCheckBox)
from PyQt5.QtGui import QPixmap, QIcon, QImage, QFont, QPalette, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class ImageProcessor(QThread):
    progress_updated = pyqtSignal(int)
    processing_completed = pyqtSignal(np.ndarray, str)
    
    def __init__(self, image_array, operation, mode, key=None, seed=None):
        super().__init__()
        self.image_array = image_array
        self.operation = operation
        self.mode = mode  # 'encrypt' or 'decrypt'
        self.key = key
        self.seed = seed
        self.result = None
        self.message = ""
        
    def run(self):
        try:
            height, width, channels = self.image_array.shape
            total_pixels = height * width
            
            # Create a copy of the image to work with
            result = self.image_array.copy()
            
            if self.operation == "XOR Cipher":
                if not self.key:
                    self.message = "Error: Key is required for XOR cipher"
                    return
                    
                key_value = int(self.key) % 256
                
                for h in range(height):
                    for w in range(width):
                        result[h, w] = self.image_array[h, w] ^ key_value
                        if (h * width + w) % 1000 == 0:
                            progress = int(100 * (h * width + w) / total_pixels)
                            self.progress_updated.emit(progress)
                            
            elif self.operation == "Reverse Color Channels":
                # In both encrypt and decrypt, we swap R and B channels (operation is its own inverse)
                result[:, :, 0], result[:, :, 2] = self.image_array[:, :, 2].copy(), self.image_array[:, :, 0].copy()
                self.progress_updated.emit(100)
                
            elif self.operation == "Pixel Shuffle":
                if not self.seed:
                    self.message = "Error: Seed is required for pixel shuffle"
                    return
                    
                seed_value = int(self.seed)
                np.random.seed(seed_value)
                
                # Flatten the image to 1D array for shuffling
                flat_img = self.image_array.reshape(-1)
                indices = np.arange(flat_img.size)
                np.random.shuffle(indices)
                
                # Create the shuffled/unshuffled image
                flat_result = np.zeros_like(flat_img)
                
                if self.mode == 'encrypt':
                    # Shuffling
                    for i in range(len(indices)):
                        flat_result[indices[i]] = flat_img[i]
                        if i % 100000 == 0:
                            self.progress_updated.emit(int(100 * i / len(indices)))
                else:
                    # Unshuffling (decrypt)
                    for i in range(len(indices)):
                        flat_result[i] = flat_img[indices[i]]
                        if i % 100000 == 0:
                            self.progress_updated.emit(int(100 * i / len(indices)))
                
                # Reshape back to original image dimensions
                result = flat_result.reshape(self.image_array.shape)
                self.progress_updated.emit(100)
                
            elif self.operation == "Bit Rotation":
                if not self.key:
                    self.message = "Error: Rotation amount is required"
                    return
                    
                rotation = int(self.key) % 8
                if self.mode == 'decrypt':
                    # For decryption, rotate in the opposite direction
                    rotation = (8 - rotation) % 8
                
                for h in range(height):
                    for w in range(width):
                        for c in range(channels):
                            # Rotate the bits by the given amount
                            pixel = int(self.image_array[h, w, c])
                            result[h, w, c] = ((pixel << rotation) | (pixel >> (8 - rotation))) & 0xFF
                        
                        if (h * width + w) % 1000 == 0:
                            progress = int(100 * (h * width + w) / total_pixels)
                            self.progress_updated.emit(progress)
                
            elif self.operation == "Invert":
                result = 255 - self.image_array
                self.progress_updated.emit(100)
                
            elif self.operation == "Grid Scramble":
                grid_size = 8
                if self.key:
                    grid_size = max(2, min(32, int(self.key)))
                
                # Ensure dimensions are multiples of grid_size
                usable_h = height - (height % grid_size)
                usable_w = width - (width % grid_size)
                
                if self.seed:
                    np.random.seed(int(self.seed))
                
                # Generate grid indices
                grid_h = usable_h // grid_size
                grid_w = usable_w // grid_size
                grid_indices = np.arange(grid_h * grid_w).reshape(grid_h, grid_w)
                flat_indices = grid_indices.flatten()
                np.random.shuffle(flat_indices)
                scrambled_indices = flat_indices.reshape(grid_h, grid_w)
                
                # Apply grid scrambling/unscrambling
                result_temp = result.copy()
                
                if self.mode == 'encrypt':
                    # Scrambling
                    for h in range(grid_h):
                        for w in range(grid_w):
                            target_h, target_w = np.unravel_index(scrambled_indices[h, w], (grid_h, grid_w))
                            
                            h_start, h_end = h * grid_size, (h + 1) * grid_size
                            w_start, w_end = w * grid_size, (w + 1) * grid_size
                            
                            target_h_start, target_h_end = target_h * grid_size, (target_h + 1) * grid_size
                            target_w_start, target_w_end = target_w * grid_size, (target_w + 1) * grid_size
                            
                            result[h_start:h_end, w_start:w_end] = self.image_array[target_h_start:target_h_end, 
                                                                                    target_w_start:target_w_end]
                else:
                    # Unscrambling (decrypt)
                    for h in range(grid_h):
                        for w in range(grid_w):
                            target_h, target_w = np.unravel_index(scrambled_indices[h, w], (grid_h, grid_w))
                            
                            h_start, h_end = h * grid_size, (h + 1) * grid_size
                            w_start, w_end = w * grid_size, (w + 1) * grid_size
                            
                            target_h_start, target_h_end = target_h * grid_size, (target_h + 1) * grid_size
                            target_w_start, target_w_end = target_w * grid_size, (target_w + 1) * grid_size
                            
                            result[target_h_start:target_h_end, target_w_start:target_w_end] = self.image_array[h_start:h_end, 
                                                                                                            w_start:w_end]
                
                progress = 100
                self.progress_updated.emit(progress)

            elif self.operation == "Shift RGB Values":
                if not self.key:
                    self.message = "Error: Shift amount is required"
                    return
                    
                shift_amount = int(self.key) % 256
                if self.mode == 'decrypt':
                    shift_amount = (256 - shift_amount) % 256
                
                for h in range(height):
                    for w in range(width):
                        for c in range(channels):
                            # Add or subtract the shift amount
                            result[h, w, c] = (self.image_array[h, w, c] + shift_amount) % 256
                    
                    if h % 10 == 0:
                        progress = int(100 * h / height)
                        self.progress_updated.emit(progress)
            
            self.result = result
            self.processing_completed.emit(result, "Operation completed successfully")
            
        except Exception as e:
            self.message = f"Error: {str(e)}"
            self.processing_completed.emit(None, self.message)

class ImageEncryptionTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SecureImage - Advanced Image Encryption Tool")
        self.setMinimumSize(1200, 800)
        
        self.original_image = None
        self.processed_image = None
        self.current_image_array = None
        self.processing_history = []
        self.operation_history = []  # Keep track of operations for decryption
        
        # Set app style
        self.setup_style()
        self.init_ui()
        
    def setup_style(self):
        # Set application style
        app = QApplication.instance()
        app.setStyle('Fusion')
        
        # Create custom palette
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(35, 35, 35))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, QColor(35, 35, 35))
        
        app.setPalette(palette)
        
    def init_ui(self):
        # Main layout with splitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left panel (images)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Image displays
        images_splitter = QSplitter(Qt.Horizontal)
        
        # Original image frame
        original_frame = QFrame()
        original_frame.setFrameShape(QFrame.StyledPanel)
        original_layout = QVBoxLayout(original_frame)
        original_title = QLabel("Original Image")
        original_title.setAlignment(Qt.AlignCenter)
        original_title.setFont(QFont("Arial", 12, QFont.Bold))
        self.original_label = QLabel()
        self.original_label.setAlignment(Qt.AlignCenter)
        self.original_label.setStyleSheet("background-color: #2a2a2a; border-radius: 5px;")
        self.original_label.setMinimumSize(400, 300)
        self.original_label.setText("No image loaded")
        original_layout.addWidget(original_title)
        original_layout.addWidget(self.original_label)
        
        # Processed image frame
        processed_frame = QFrame()
        processed_frame.setFrameShape(QFrame.StyledPanel)
        processed_layout = QVBoxLayout(processed_frame)
        processed_title = QLabel("Processed Image")
        processed_title.setAlignment(Qt.AlignCenter)
        processed_title.setFont(QFont("Arial", 12, QFont.Bold))
        self.processed_label = QLabel()
        self.processed_label.setAlignment(Qt.AlignCenter)
        self.processed_label.setStyleSheet("background-color: #2a2a2a; border-radius: 5px;")
        self.processed_label.setMinimumSize(400, 300)
        self.processed_label.setText("No processing applied")
        processed_layout.addWidget(processed_title)
        processed_layout.addWidget(self.processed_label)
        
        images_splitter.addWidget(original_frame)
        images_splitter.addWidget(processed_frame)
        left_layout.addWidget(images_splitter)
        
        # Progress bar
        progress_group = QGroupBox("Processing Progress")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% complete")
        progress_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_layout)
        left_layout.addWidget(progress_group)
        
        # Action buttons
        action_group = QGroupBox("Image Operations")
        action_layout = QVBoxLayout()
        
        # Action buttons row 1
        action_buttons1 = QHBoxLayout()
        
        # Load image button
        self.load_btn = QPushButton("Load Image")
        self.load_btn.setIcon(QIcon.fromTheme("document-open"))
        self.load_btn.setMinimumHeight(40)
        self.load_btn.clicked.connect(self.load_image)
        action_buttons1.addWidget(self.load_btn)
        
        # Save image button
        self.save_btn = QPushButton("Save Processed Image")
        self.save_btn.setIcon(QIcon.fromTheme("document-save"))
        self.save_btn.setMinimumHeight(40)
        self.save_btn.clicked.connect(self.save_image)
        self.save_btn.setEnabled(False)
        action_buttons1.addWidget(self.save_btn)
        
        action_layout.addLayout(action_buttons1)
        
        # Action buttons row 2
        action_buttons2 = QHBoxLayout()
        
        # Reset button
        self.reset_btn = QPushButton("Reset to Original")
        self.reset_btn.setIcon(QIcon.fromTheme("edit-undo"))
        self.reset_btn.setMinimumHeight(40)
        self.reset_btn.clicked.connect(self.reset_to_original)
        self.reset_btn.setEnabled(False)
        action_buttons2.addWidget(self.reset_btn)
        
        # Undo button
        self.undo_btn = QPushButton("Undo Last Operation")
        self.undo_btn.setIcon(QIcon.fromTheme("edit-undo"))
        self.undo_btn.setMinimumHeight(40)
        self.undo_btn.clicked.connect(self.undo_last_operation)
        self.undo_btn.setEnabled(False)
        action_buttons2.addWidget(self.undo_btn)
        
        action_layout.addLayout(action_buttons2)
        
        # Auto decrypt button
        self.auto_decrypt_btn = QPushButton("Auto Decrypt")
        self.auto_decrypt_btn.setIcon(QIcon.fromTheme("document-decrypt"))
        self.auto_decrypt_btn.setMinimumHeight(40)
        self.auto_decrypt_btn.clicked.connect(self.auto_decrypt)
        self.auto_decrypt_btn.setEnabled(False)
        action_layout.addWidget(self.auto_decrypt_btn)
        
        action_group.setLayout(action_layout)
        left_layout.addWidget(action_group)
        
        # Right panel (encryption controls)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Mode selection
        mode_group = QGroupBox("Operation Mode")
        mode_layout = QHBoxLayout()
        
        self.encrypt_radio = QRadioButton("Encrypt")
        self.encrypt_radio.setChecked(True)
        self.decrypt_radio = QRadioButton("Decrypt")
        
        mode_layout.addWidget(self.encrypt_radio)
        mode_layout.addWidget(self.decrypt_radio)
        mode_group.setLayout(mode_layout)
        right_layout.addWidget(mode_group)
        
        # Encryption methods
        operations_group = QGroupBox("Image Processing Methods")
        operations_layout = QVBoxLayout()
        
        # Operation selection
        operation_layout = QFormLayout()
        self.operation_combo = QComboBox()
        self.operation_combo.addItems([
            "XOR Cipher", 
            "Shift RGB Values",
            "Reverse Color Channels", 
            "Pixel Shuffle", 
            "Bit Rotation", 
            "Invert", 
            "Grid Scramble"
        ])
        self.operation_combo.currentTextChanged.connect(self.update_parameter_visibility)
        operation_layout.addRow("Operation:", self.operation_combo)
        operations_layout.addLayout(operation_layout)
        
        # Parameters group
        params_group = QGroupBox("Operation Parameters")
        params_layout = QVBoxLayout()
        
        # Key input
        key_layout = QFormLayout()
        self.key_input = QSpinBox()
        self.key_input.setRange(0, 255)
        self.key_input.setValue(42)
        key_layout.addRow("Key Value:", self.key_input)
        params_layout.addLayout(key_layout)
        
        # Seed input
        seed_layout = QFormLayout()
        self.seed_input = QSpinBox()
        self.seed_input.setRange(0, 99999)
        self.seed_input.setValue(12345)
        seed_layout.addRow("Seed Value:", self.seed_input)
        params_layout.addLayout(seed_layout)
        
        self.key_layout = key_layout
        self.seed_layout = seed_layout
        
        params_group.setLayout(params_layout)
        operations_layout.addWidget(params_group)
        
        # Parameter description
        self.param_description = QLabel()
        self.param_description.setWordWrap(True)
        self.param_description.setStyleSheet("background-color: #2a2a2a; padding: 10px; border-radius: 5px;")
        operations_layout.addWidget(self.param_description)
        
        # Process button
        self.process_btn = QPushButton("Apply Operation")
        self.process_btn.setIcon(QIcon.fromTheme("system-run"))
        self.process_btn.setMinimumHeight(50)
        self.process_btn.clicked.connect(self.apply_operation)
        self.process_btn.setEnabled(False)
        operations_layout.addWidget(self.process_btn)
        
        operations_group.setLayout(operations_layout)
        right_layout.addWidget(operations_group)
        
        # Help section
        help_group = QGroupBox("Help & Information")
        help_layout = QVBoxLayout()
        
        help_text = QLabel(
            "<b>Image Operations:</b><br>"
            "• <u>XOR Cipher</u>: Applies XOR with the key value. Same key decrypts.<br>"
            "• <u>Shift RGB Values</u>: Adds key value to each pixel. Subtract to decrypt.<br>"
            "• <u>Reverse Color Channels</u>: Swaps R and B channels. Apply again to decrypt.<br>"
            "• <u>Pixel Shuffle</u>: Randomizes pixels using seed. Use same seed to decrypt.<br>"
            "• <u>Bit Rotation</u>: Rotates each pixel's bits. Rotate in opposite direction to decrypt.<br>"
            "• <u>Invert</u>: Creates a negative image. Apply again to decrypt.<br>"
            "• <u>Grid Scramble</u>: Scrambles grid cells. Use same key/seed to decrypt.<br><br>"
            "<b>Tips:</b><br>"
            "• Use 'Auto Decrypt' to automatically reverse all operations.<br>"
            "• Apply multiple operations for stronger encryption.<br>"
            "• Record your keys and seeds to ensure proper decryption!"
        )
        help_text.setWordWrap(True)
        help_text.setTextFormat(Qt.RichText)
        help_layout.addWidget(help_text)
        help_group.setLayout(help_layout)
        right_layout.addWidget(help_group)
        
        # Add stretch to fill space
        right_layout.addStretch()
        
        # Add widgets to splitter
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setStretchFactor(0, 2)
        main_splitter.setStretchFactor(1, 1)
        
        # Set as central widget
        self.setCentralWidget(main_splitter)
        
        # Initialize UI state
        self.update_parameter_visibility()
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def update_parameter_visibility(self):
        operation = self.operation_combo.currentText()
        
        # Hide all parameter inputs first
        for widget in self.key_layout.findChildren(QWidget):
            widget.hide()
        for widget in self.seed_layout.findChildren(QWidget):
            widget.hide()
        
        # Update visibility and description based on operation
        if operation == "XOR Cipher":
            for widget in self.key_layout.findChildren(QWidget):
                widget.show()
            self.param_description.setText(
                "XOR Cipher: Applies bitwise XOR with the key value to each pixel. "
                "Use the same key to encrypt and decrypt."
            )
            
        elif operation == "Reverse Color Channels":
            self.param_description.setText(
                "Reverse Color Channels: Swaps the Red and Blue color channels. "
                "This operation is its own inverse - apply it again to decrypt."
            )
            
        elif operation == "Pixel Shuffle":
            for widget in self.seed_layout.findChildren(QWidget):
                widget.show()
            self.param_description.setText(
                "Pixel Shuffle: Randomly rearranges pixels using a seed value. "
                "Use the same seed and the Decrypt mode to restore the original image."
            )
            
        elif operation == "Bit Rotation":
            for widget in self.key_layout.findChildren(QWidget):
                widget.show()
            self.param_description.setText(
                "Bit Rotation: Rotates each pixel's bits by the specified amount (0-7). "
                "When decrypting, the rotation is performed in the opposite direction."
            )
            
        elif operation == "Invert":
            self.param_description.setText(
                "Invert: Creates a negative of the image by inverting all pixel values. "
                "Apply this operation again to restore the original image."
            )
            
        elif operation == "Grid Scramble":
            for widget in self.key_layout.findChildren(QWidget):
                widget.show()
            for widget in self.seed_layout.findChildren(QWidget):
                widget.show()
            self.param_description.setText(
                "Grid Scramble: Divides the image into a grid (size determined by key) "
                "and scrambles the cells using the seed value. "
                "Use the same key and seed with Decrypt mode to restore."
            )
            
        elif operation == "Shift RGB Values":
            for widget in self.key_layout.findChildren(QWidget):
                widget.show()
            self.param_description.setText(
                "Shift RGB Values: Adds the key value to each pixel component. "
                "When decrypting, the key value is subtracted instead."
            )
    
    def load_image(self):
        file_dialog = QFileDialog()
        image_path, _ = file_dialog.getOpenFileName(
            self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if image_path:
            try:
                # Load image
                self.original_image = Image.open(image_path)
                
                # Convert to RGB if needed
                if self.original_image.mode != 'RGB':
                    self.original_image = self.original_image.convert('RGB')
                
                # Convert to numpy array
                self.current_image_array = np.array(self.original_image)
                
                # Display original image
                pixmap = self.convert_to_pixmap(self.original_image)
                self.original_label.setPixmap(pixmap)
                
                # Reset state
                self.processing_history = []
                self.operation_history = []
                self.processed_image = None
                self.processed_label.setText("No processing applied")
                self.processed_label.setPixmap(QPixmap())
                
                # Update UI state
                self.process_btn.setEnabled(True)
                self.reset_btn.setEnabled(False)
                self.undo_btn.setEnabled(False)
                self.save_btn.setEnabled(False)
                self.auto_decrypt_btn.setEnabled(False)
                
                # Update status
                filename = os.path.basename(image_path)
                self.statusBar().showMessage(f"Loaded: {filename} ({self.original_image.width}x{self.original_image.height})")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
    
    def convert_to_pixmap(self, pil_image):
        # Convert PIL image to QPixmap
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
            
        # Convert PIL Image to QImage
        image_data = pil_image.tobytes("raw", "RGB")
        width, height = pil_image.size
        q_image = QImage(image_data, width, height, width * 3, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_image)
        
        # Scale pixmap to fit the label while maintaining aspect ratio
        return pixmap.scaled(self.original_label.width(), self.original_label.height(), 
                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
    def apply_operation(self):
        if self.current_image_array is None:
            return
            
        # Get operation settings
        operation = self.operation_combo.currentText()
        mode = 'decrypt' if self.decrypt_radio.isChecked() else 'encrypt'
        key = str(self.key_input.value()) if hasattr(self, 'key_input') else None
        seed = str(self.seed_input.value()) if hasattr(self, 'seed_input') else None
        
        # Save current state for undo
        self.processing_history.append(self.current_image_array.copy())
        
        # Record operation for auto-decrypt
        if mode == 'encrypt':
            self.operation_history.append({
                'operation': operation,
                'key': key,
                'seed': seed
            })
        
        # Create and start worker thread
        self.worker = ImageProcessor(self.current_image_array, operation, mode, key, seed)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.processing_completed.connect(self.handle_processing_completed)
        
        # Disable UI during processing
        self.process_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.undo_btn.setEnabled(False)
        self.auto_decrypt_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        # Update status
        self.statusBar().showMessage(f"Applying {operation} ({mode} mode)...")
        
        # Start processing
        self.worker.start()
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def handle_processing_completed(self, result, message):
        # Re-enable UI
        self.process_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        
        if result is not None:
            # Update current image array
            self.current_image_array = result
            
            # Convert to PIL image
            processed_image = Image.fromarray(result.astype('uint8'))
            self.processed_image = processed_image
            
            # Display processed image
            pixmap = self.convert_to_pixmap(processed_image)
            self.processed_label.setPixmap(pixmap)
            
            # Update UI state
            self.save_btn.setEnabled(True)
            self.reset_btn.setEnabled(True)
            self.undo_btn.setEnabled(len(self.processing_history) > 0)
            self.auto_decrypt_btn.setEnabled(len(self.operation_history) > 0)
            
            # Update status
            self.statusBar().showMessage("Operation completed successfully")
        else:
            # Show error message
            QMessageBox.warning(self, "Error", message)
            self.statusBar().showMessage(f"Error: {message}")
    
    def save_image(self):
        if self.processed_image is None:
            return
            
        file_dialog = QFileDialog()
        save_path, _ = file_dialog.getSaveFileName(
            self, "Save Processed Image", "", 
            "PNG Files (*.png);;JPEG Files (*.jpg);;BMP Files (*.bmp)"
        )
        
        if save_path:
            try:
                self.processed_image.save(save_path)
                QMessageBox.information(self, "Success", "Image saved successfully!")
                self.statusBar().showMessage(f"Image saved to: {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save image: {str(e)}")
    
    def reset_to_original(self):
        if self.original_image is None:
            return
            
        # Reset current image to original
        self.current_image_array = np.array(self.original_image)
        
        # Clear processed image display
        self.processed_label.setText("No processing applied")
        self.processed_label.setPixmap(QPixmap())
        self.processed_image = None
        
        # Update UI state
        self.save_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.undo_btn.setEnabled(False)
        self.auto_decrypt_btn.setEnabled(False)
        
        # Clear history
        self.processing_history = []
        self.operation_history = []
        
        # Update status
        self.statusBar().showMessage("Reset to original image")
    
    def undo_last_operation(self):
        if not self.processing_history:
            return
            
        # Restore previous state
        self.current_image_array = self.processing_history.pop()
        
        # Remove last operation from history if we're undoing an encrypt operation
        if self.operation_history:
            self.operation_history.pop()
        
        # Convert to PIL image and display
        restored_image = Image.fromarray(self.current_image_array.astype('uint8'))
        self.processed_image = restored_image
        pixmap = self.convert_to_pixmap(restored_image)
        self.processed_label.setPixmap(pixmap)
        
        # Update UI state
        self.undo_btn.setEnabled(len(self.processing_history) > 0)
        self.auto_decrypt_btn.setEnabled(len(self.operation_history) > 0)
        
        # Update status
        self.statusBar().showMessage("Undid last operation")
    
    def auto_decrypt(self):
        """Automatically decrypt all operations in reverse order"""
        if not self.operation_history or self.current_image_array is None:
            return
        
        # Confirm with user
        confirm = QMessageBox.question(
            self, 
            "Confirm Auto Decrypt", 
            "This will attempt to decrypt all operations in reverse order. Continue?",
            QMessageBox.Yes | QMessageBox.No, 
            QMessageBox.Yes
        )
        
        if confirm != QMessageBox.Yes:
            return
        
        # Save current state
        self.processing_history.append(self.current_image_array.copy())
        
        # Start decryption process
        self.statusBar().showMessage("Starting auto-decryption...")
        self.progress_bar.setValue(0)
        
        # Disable UI during processing
        self.disable_ui_during_processing()
        
        # Process operations in reverse order
        reversed_operations = self.operation_history.copy()
        reversed_operations.reverse()
        
        # Create result image
        result = self.current_image_array.copy()
        
        try:
            total_ops = len(reversed_operations)
            for i, op in enumerate(reversed_operations):
                # Process each operation
                operation = op['operation']
                key = op['key']
                seed = op['seed']
                
                # Update progress
                self.progress_bar.setValue(int(100 * i / total_ops))
                self.statusBar().showMessage(f"Auto-decrypting: {operation} ({i+1}/{total_ops})")
                QApplication.processEvents()  # Keep UI responsive
                
                # Process the image
                processor = ImageProcessor(result, operation, 'decrypt', key, seed)
                processor.run()  # Run synchronously since we're already in a loop
                
                if processor.result is not None:
                    result = processor.result
                else:
                    # Show error and exit loop
                    QMessageBox.warning(self, "Error", f"Auto-decrypt failed: {processor.message}")
                    break
            
            # Update current image
            self.current_image_array = result
            
            # Convert to PIL image and display
            decrypted_image = Image.fromarray(result.astype('uint8'))
            self.processed_image = decrypted_image
            pixmap = self.convert_to_pixmap(decrypted_image)
            self.processed_label.setPixmap(pixmap)
            
            # Clear operation history since we've reversed everything
            self.operation_history = []
            
            # Update UI state
            self.save_btn.setEnabled(True)
            self.reset_btn.setEnabled(True)
            self.undo_btn.setEnabled(len(self.processing_history) > 0)
            self.auto_decrypt_btn.setEnabled(False)
            
            self.statusBar().showMessage("Auto-decryption completed successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Auto-decrypt failed: {str(e)}")
            self.statusBar().showMessage(f"Error during auto-decryption: {str(e)}")
        
        # Re-enable UI
        self.enable_ui_after_processing()
    
    def disable_ui_during_processing(self):
        """Disable UI elements during processing"""
        self.process_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.reset_btn.setEnabled(False)
        self.undo_btn.setEnabled(False)
        self.auto_decrypt_btn.setEnabled(False)
        self.encrypt_radio.setEnabled(False)
        self.decrypt_radio.setEnabled(False)
        self.operation_combo.setEnabled(False)
    
    def enable_ui_after_processing(self):
        """Re-enable UI elements after processing"""
        self.process_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        self.save_btn.setEnabled(self.processed_image is not None)
        self.reset_btn.setEnabled(self.processed_image is not None)
        self.undo_btn.setEnabled(len(self.processing_history) > 0)
        self.auto_decrypt_btn.setEnabled(len(self.operation_history) > 0)
        self.encrypt_radio.setEnabled(True)
        self.decrypt_radio.setEnabled(True)
        self.operation_combo.setEnabled(True)
    
    def resizeEvent(self, event):
        """Handle window resize events to update image displays"""
        super().resizeEvent(event)
        
        # Update original image display if needed
        if self.original_image is not None:
            pixmap = self.convert_to_pixmap(self.original_image)
            self.original_label.setPixmap(pixmap)
        
        # Update processed image display if needed
        if self.processed_image is not None:
            pixmap = self.convert_to_pixmap(self.processed_image)
            self.processed_label.setPixmap(pixmap)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for a consistent look
    
    # Set application icon
    app_icon = QIcon.fromTheme("security-high")
    app.setWindowIcon(app_icon)
    
    # Create and show window
    window = ImageEncryptionTool()
    window.show()
    sys.exit(app.exec_())