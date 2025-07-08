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
    log_coordinates: bool = True # save coordinates to file (includes camera offset!)

    render_test: bool = False # open preview of display

    def __init__(self, real_images: bool = True, stellarium_server: bool = True):
        OperationManager.use_real_images = real_images
        OperationManager.stellarium_server = stellarium_server

