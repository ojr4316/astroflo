class OperationManager:

    mode: int = 0

    ### Settings

    ### Feature Flags
    use_real_images: bool = True
    stellarium_server: bool = True
    render_test: bool = True
    perform_analysis: bool = True

    def __init__(self, real_images: bool = True, stellarium_server: bool = True):
        OperationManager.use_real_images = real_images
        OperationManager.stellarium_server = stellarium_server

