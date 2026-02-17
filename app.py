"""Local development entrypoint for the MinexPy-GUI Flask application."""

from minexpygui import create_app


# Build the Flask application through the package-level app factory.
app = create_app()


if __name__ == "__main__":
    # Run the app locally. This project is designed for local researcher workflows.
    app.run(debug=True)
