from utils import is_pi

class OperationManager:

    mode: int = 0

    ### Settings

    ### Feature Flags
    # default options
    use_real_images: bool = True # Use cameras images by default, else use test image
    stellarium_server: bool = False#is_pi() # Telescope Control Stellarium Plugin
    perform_analysis: bool = False # add each image to a stat analyzer
    save_over: bool = True # continuously save images over existing file (for preview)
    drift: bool = True # drift render of sky at expected rate
    log_coordinates: bool = not is_pi() # save coordinates to file (includes camera offset!)
    use_real_solver: bool = False # use astrometric solver on images
    dynamic_adjust: bool = False # Dynamically adjust exposure based on success rate

    render_test: bool = False # open preview of display
