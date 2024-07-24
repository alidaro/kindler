document.addEventListener('DOMContentLoaded', function() {
    const bookForm = document.getElementById('book-form');
    const bookTitleInput = document.getElementById('book-title');
    const generateBtn = document.getElementById('generate-btn');
    const loadingDiv = document.getElementById('loading');
    const pricingLink = document.getElementById('pricing-link');

    bookForm.addEventListener('submit', function(event) {
        event.preventDefault();
        const bookTitle = bookTitleInput.value.trim();
        if (bookTitle === '') {
            alert('Please enter a book title');
            return;
        }

        // Show loading spinner
        loadingDiv.style.display = 'block';
        generateBtn.disabled = true;

        // Send request to backend
        fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `book_title=${encodeURIComponent(bookTitle)}`
        })
        .then(response => response.json())
        .then(data => {
            // Hide loading spinner
            loadingDiv.style.display = 'none';
            generateBtn.disabled = false;
            
            // Redirect to the download page
            window.location.href = `/download-page/${data.filename}`;
        })
        .catch(error => {
            console.error('Error:', error);
            // Hide loading spinner
            loadingDiv.style.display = 'none';
            alert('An error occurred while generating the book');
            generateBtn.disabled = false;
        });
    });

    // Redirect to YouTube when Pricing link is clicked
    pricingLink.addEventListener('click', function(event) {
        event.preventDefault();
        window.location.href = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
    });
});