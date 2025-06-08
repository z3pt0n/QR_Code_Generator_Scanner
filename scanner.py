
import cv2
import glfw
import numpy as np
import pygame
import webbrowser
import time
from OpenGL.GL import *
from OpenGL.GLU import *
from tkinter import Tk, filedialog

# Initialize pygame for text rendering
pygame.init()
font = pygame.font.SysFont('Helvetica', 18)

def detect_qr_code(image):
    """Detect QR code in the given image"""
    detector = cv2.QRCodeDetector()
    data, bbox, _ = detector.detectAndDecode(image)
    return data, bbox

def draw_bbox(bbox):
    """Draw bounding box around QR code"""
    if bbox is not None:
        bbox = bbox[0]
        glBegin(GL_LINES)
        for i in range(len(bbox)):
            glVertex2f(bbox[i][0], bbox[i][1])
            glVertex2f(bbox[(i+1) % len(bbox)][0], bbox[(i+1) % len(bbox)][1])
        glEnd()

def draw_text(text, x, y):
    """Render text using pygame and OpenGL"""
    text_surface = font.render(text, True, (0, 0, 0, 255))  # Black text for better visibility
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    glRasterPos2f(x, y)
    glDrawPixels(text_surface.get_width(), text_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, text_data)

def display(image, data, bbox, width, height):
    """Display the image with bounding box and QR code data"""
    # Calculate scaling factor to fit the window
    img_h, img_w = image.shape[:2]
    scale_w = width / img_w
    scale_h = (height - 100) / img_h  # Leave room for buttons
    scale = min(scale_w, scale_h)
    
    # If image is too large, resize it
    if scale < 1.0:
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # Flip the image vertically for OpenGL
    image_flipped = np.flipud(image)
    
    # Calculate position to center the image
    x_offset = (width - image_flipped.shape[1]) // 2
    y_offset = (height - image_flipped.shape[0] - 50) // 2 + 50  # Center + leave space for buttons
    
    # Clear the screen
    glClear(GL_COLOR_BUFFER_BIT)
    
    # Move to the centered position
    glRasterPos2i(x_offset, y_offset)
    
    # Draw the image
    glDrawPixels(image_flipped.shape[1], image_flipped.shape[0], GL_RGB, GL_UNSIGNED_BYTE, image_flipped)

    # Draw bounding box if detected
    if bbox is not None:
        glColor3f(1.0, 0.0, 0.0)  # Red bounding box
        draw_bbox(bbox)

    # Display QR code data if available
    if data:
        glColor3f(0.0, 1.0, 0.0)  # Green text
        draw_text(f"QR Data: {data}", 10, height - 30)

def open_website(url, last_url):
    """Open URL in web browser if it's a new URL"""
    if url != last_url:
        print("Opening URL:", url)
        try:
            webbrowser.open(url, new=2)
            return url  # Return the opened URL
        except Exception as e:
            print("Error opening URL:", e)
    return last_url

def open_image_file():
    """Open image file dialog and return the selected image"""
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
    root.destroy()
    
    if file_path:
        try:
            image = cv2.imread(file_path)
            if image is None:
                print(f"Error: Could not read image file: {file_path}")
                return None
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        except Exception as e:
            print(f"Error opening image: {e}")
            return None
    return None

def main():
    # Initialize GLFW
    if not glfw.init():
        print("Failed to initialize GLFW")
        return

    # Set window dimensions
    width, height = 800, 600
    
    # Create window with correct hints
    glfw.window_hint(glfw.RESIZABLE, False)  # Make window non-resizable
    glfw.window_hint(glfw.VISIBLE, True)     # Make window visible
    
    # Create window
    window = glfw.create_window(width, height, "QR Code Scanner", None, None)
    if not window:
        print("Failed to create GLFW window")
        glfw.terminate()
        return

    # Make OpenGL context current
    glfw.make_context_current(window)
    
    # Center window on screen
    screen_width, screen_height = glfw.get_video_mode(glfw.get_primary_monitor()).size
    window_x = (screen_width - width) // 2
    window_y = (screen_height - height) // 2
    glfw.set_window_pos(window, window_x, window_y)

    # Try to open camera
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Warning: Could not open camera. Gallery mode only.")
            has_camera = False
        else:
            has_camera = True
    except Exception as e:
        print(f"Camera error: {e}")
        has_camera = False

    # Set up OpenGL projection and parameters
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluOrtho2D(0, width, 0, height)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    
    # Set pixel storage mode
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
    
    # Enable alpha blending for text
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Application state variables
    use_camera = has_camera
    image_from_gallery = None
    last_url_opened = None
    gallery_mode_start_time = 0
    current_qr_data = None

    def mouse_button_callback(window, button, action, mods):
        """Handle mouse clicks on buttons"""
        nonlocal use_camera, image_from_gallery, last_url_opened, gallery_mode_start_time, current_qr_data
        
        if button == glfw.MOUSE_BUTTON_LEFT and action == glfw.PRESS:
            xpos, ypos = glfw.get_cursor_pos(window)
            ypos = height - ypos  # Convert to OpenGL coordinates
            
            # Gallery button: x=[20, 220], y=[10, 40]
            if 20 <= xpos <= 220 and 10 <= ypos <= 40:
                image_from_gallery = open_image_file()
                if image_from_gallery is not None:
                    use_camera = False
                    gallery_mode_start_time = time.time()
                    current_qr_data = None
                    last_url_opened = None
            
            # Reset button: x=[240, 360], y=[10, 40]
            elif 240 <= xpos <= 360 and 10 <= ypos <= 40:
                last_url_opened = None
                current_qr_data = None
                if not has_camera:
                    image_from_gallery = None
            
            # Camera/Gallery toggle button: x=[380, 580], y=[10, 40]
            elif has_camera and 380 <= xpos <= 580 and 10 <= ypos <= 40:
                use_camera = not use_camera
                if use_camera:
                    current_qr_data = None
                    last_url_opened = None

    # Set mouse callback function
    glfw.set_mouse_button_callback(window, mouse_button_callback)

    def draw_buttons():
        """Draw UI buttons"""
        # Bottom bar background
        glColor3f(0.2, 0.2, 0.2)  # Dark gray
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(width, 0)
        glVertex2f(width, 50)
        glVertex2f(0, 50)
        glEnd()
        
        # Gallery import button
        glColor3f(0.5, 0.5, 1.0)  # Lighter Blue
        glBegin(GL_QUADS)
        glVertex2f(20, 10)
        glVertex2f(220, 10)
        glVertex2f(220, 40)
        glVertex2f(20, 40)
        glEnd()
        draw_text("Import from Gallery", 30, 15)
        
        # Reset button
        glColor3f(1.0, 0.5, 0.5)  # Lighter Red
        glBegin(GL_QUADS)
        glVertex2f(240, 10)
        glVertex2f(360, 10)
        glVertex2f(360, 40)
        glVertex2f(240, 40)
        glEnd()
        draw_text("Reset", 270, 15)
        
        # Camera/Gallery toggle (only if camera is available)
        if has_camera:
            glColor3f(0.5, 1.0, 0.5)  # Lighter Green
            glBegin(GL_QUADS)
            glVertex2f(380, 10)
            glVertex2f(580, 10)
            glVertex2f(580, 40)
            glVertex2f(380, 40)
            glEnd()
            if use_camera:
                draw_text("Switch to Gallery", 400, 15)
            else:
                draw_text("Switch to Camera", 400, 15)

    # Main loop
    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # Process camera or gallery image
        if use_camera and has_camera:
            ret, frame = cap.read()
            if not ret:
                print("Error: Could not read frame.")
                time.sleep(0.1)  # Avoid busy waiting
                continue

            # Convert and detect QR code
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            data, bbox = detect_qr_code(frame)
            
            # Update current QR data
            if data:
                current_qr_data = data
                
                # Open website if it's a URL
                if data.startswith('http'):
                    last_url_opened = open_website(data, last_url_opened)
            
            # Clear and setup for full window
            glViewport(0, 0, width, height)
            # Display the frame (directly draw on the full window)
            display(frame, current_qr_data, bbox, width, height)

        elif image_from_gallery is not None:
            # Process gallery image
            data, bbox = detect_qr_code(image_from_gallery)
            
            # Update current QR data
            if data:
                current_qr_data = data
                
                # Open website if it's a URL
                if data.startswith('http'):
                    last_url_opened = open_website(data, last_url_opened)
            
            # Clear and setup for full window
            glViewport(0, 0, width, height)
            # Display the image
            display(image_from_gallery, current_qr_data, bbox, width, height)
            
            # Don't automatically switch back to camera mode
            # Keep gallery mode until user chooses to switch
        else:
            # Display blank screen with instructions
            glColor3f(1.0, 1.0, 1.0)
            draw_text("No image loaded. Click 'Import from Gallery' to continue.", 200, 300)

        # Draw UI buttons
        draw_buttons()

        # Swap buffers and poll events
        glfw.swap_buffers(window)
        glfw.poll_events()

    # Clean up resources
    if has_camera:
        cap.release()
    pygame.quit()
    glfw.terminate()

if __name__ == "__main__":
    main()
