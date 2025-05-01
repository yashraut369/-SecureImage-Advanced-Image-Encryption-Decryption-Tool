SecureImage: Advanced Image Encryption & Decryption Tool
SecureImage is a sophisticated tool built with PyQt5, providing robust image encryption and decryption features using modern cryptographic techniques. Secure your images with encryption algorithms like XOR, pixel shuffling, bit rotation, and more, all within an intuitive graphical user interface (GUI).

✨ Features
Multiple Encryption Methods:

🔐 XOR Cipher: Bitwise XOR encryption on pixels with a user-defined key.

🌈 RGB Shifting: Shifts RGB values by a specified key for enhanced image security.

🔄 Reverse Channels: Swaps red and blue channels for simple encryption.

🔀 Pixel Shuffle: Randomly shuffles pixel locations using a seed (for reversibility).

🔁 Bit Rotation: Rotates pixel bits to further encrypt the image.

🔳 Inversion: Inverts pixel values (255 - original value).

🔲 Grid Scramble: Divides the image into grids and scrambles them with a key.

Auto Decryption: Effortlessly reverses encryption operations to restore the original image.

🎨 User-Friendly GUI: Sleek, dark-themed interface built with PyQt5, designed for simplicity.

🧠 Smart Features:

Real-Time Progress: Displays a progress bar during encryption/decryption.

Error Handling: Instant feedback in case of issues like missing keys.

Undo & Reset: Easily revert or reset the image to its original state.

🚀 Getting Started
Clone the Repository

bash
Copy
Edit
git clone https://github.com/yashraut369/-SecureImage-Advanced-Image-Encryption-Decryption-Tool.git
cd SecureImage
Install Dependencies

bash
Copy
Edit
pip install -r requirements.txt
Run the Application

bash
Copy
Edit
python pixel_encryption.py
🧪 Supported Operations
Operation	Encryption	Decryption
XOR Cipher	✅	✅ (same key)
Pixel Shuffle	✅	✅ (same seed)
Reverse Channels	✅	✅ (same operation)
Bit Rotation	✅	✅ (reverse rotation)
Inversion	✅	✅ (same operation)
RGB Shift	✅	✅ (opposite shift)
Grid Scramble	✅	✅ (same key + seed)

📜 License
This project is licensed under the MIT License.

🤝 Contact
Created by Yash (Popeye)
GitHub: @yashraut369
