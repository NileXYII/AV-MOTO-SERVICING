// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    let debounceTimer;

    searchInput.addEventListener('input', function() {
        clearTimeout(debounceTimer);
        const query = this.value.trim();
        
        if (query.length < 2) {
            searchResults.classList.add('hidden');
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/search?query=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    searchResults.innerHTML = '';
                    
                    if (data.results.length > 0) {
                        const results = data.results.slice(0, 5).map(movie => `
                            <a href="/movie/${movie.id}" 
                               class="flex items-center gap-4 p-4 hover:bg-gray-700 transition">
                                <img src="https://image.tmdb.org/t/p/w92${movie.poster_path}" 
                                     alt="${movie.title}"
                                     class="w-12 h-18 object-cover rounded">
                                <div>
                                    <h3 class="font-semibold">${movie.title}</h3>
                                    <p class="text-sm text-gray-400">${movie.release_date.split('-')[0]}</p>
                                </div>
                            </a>
                        `).join('');
                        
                        searchResults.innerHTML = results;
                        searchResults.classList.remove('hidden');
                    } else {
                        searchResults.classList.add('hidden');
                    }
                });
        }, 300);
    });

    // Close search results when clicking outside
    document.addEventListener('click', function(e) {
        if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
            searchResults.classList.add('hidden');
        }
    });
});