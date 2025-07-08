from utils import is_pi

class OperationManager:

    mode: int = 0

    ### Settings

    ### Feature Flags
    # default options
    use_real_images: bool = True # Use cameras images by default, else use test image
    stellarium_server: bool = True # Telescope Control Stellarium Plugin
    perform_analysis: bool = True # add each image to a stat analyzer
    save_over: bool = True # continuously save images over existing file (for preview)
    drift: bool = True # drift render of sky at expected rate
    log_coordinates: bool = not is_pi() # save coordinates to file (includes camera offset!)
    use_real_solver: bool = False # use astrometric solver on images

    render_test: bool = not is_pi() # open preview of display

    def __init__(self, real_images: bool = True, stellarium_server: bool = True):
        OperationManager.use_real_images = real_images
        OperationManager.stellarium_server = stellarium_server

