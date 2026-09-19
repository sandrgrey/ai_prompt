() => {
    document.documentElement.classList.add('dark');
    // Gradio 6.27 clears the old image and awaits a render before reading
    // drop.dataTransfer. Native drag data is protected after event dispatch.
    // Snapshot File references synchronously; keep Gradio's upload/validation.
    document.addEventListener('drop', (event) => {
        if (!event.composedPath().some(node => node.id === 'source-image')) return;
        const files = Array.from(event.dataTransfer?.files || []);
        if (!files.length) return;
        const transfer = new DataTransfer();
        for (const file of files) transfer.items.add(file);
        Object.defineProperty(event, 'dataTransfer', {value: transfer});
    }, true);
}
