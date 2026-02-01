from flask import Flask, render_template_string
import base64
from analyzer import analyze_strategy

app = Flask(__name__)

@app.route('/')
def dashboard():
    img = analyze_strategy()
    plot_url = base64.b64encode(img.getvalue()).decode()
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Quantitative Finance App</title>
            <style>
                body { font-family: sans-serif; text-align: center; padding: 20px; }
                img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 4px; padding: 5px; }
            </style>
        </head>
        <body>
            <h1>Leverage for the Long Run Replication</h1>
            <img src="data:image/png;base64,{{ plot_url }}" alt="Strategy Comparison">
        </body>
        </html>
    ''', plot_url=plot_url)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
