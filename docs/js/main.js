document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const email = form.querySelector('input[type="email"]').value;
        const button = form.querySelector('button');
        const originalText = button.textContent;
        
        try {
            button.textContent = 'Processing...';
            button.disabled = true;
            
            const response = await fetch('https://api.kairos.ai/beta-signup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email }),
            });
            
            if (response.ok) {
                button.textContent = 'Success! ✓';
                button.classList.remove('bg-blue-600', 'hover:bg-blue-700');
                button.classList.add('bg-green-600', 'hover:bg-green-700');
                
                setTimeout(() => {
                    form.reset();
                    button.textContent = originalText;
                    button.classList.remove('bg-green-600', 'hover:bg-green-700');
                    button.classList.add('bg-blue-600', 'hover:bg-blue-700');
                    button.disabled = false;
                }, 3000);
            } else {
                throw new Error('Signup failed');
            }
        } catch (error) {
            button.textContent = 'Error! Try again';
            button.classList.remove('bg-blue-600', 'hover:bg-blue-700');
            button.classList.add('bg-red-600', 'hover:bg-red-700');
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('bg-red-600', 'hover:bg-red-700');
                button.classList.add('bg-blue-600', 'hover:bg-blue-700');
                button.disabled = false;
            }, 3000);
        }
    });
}); 