if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"KLEN web console — http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
