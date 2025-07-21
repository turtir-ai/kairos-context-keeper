// Smooth scroll for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Navbar scroll effect
const navbar = document.querySelector('nav');
let lastScroll = 0;

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll <= 0) {
        navbar.classList.remove('shadow-lg');
        return;
    }
    
    if (currentScroll > lastScroll) {
        // Scrolling down
        navbar.classList.add('shadow-lg');
        navbar.style.transform = 'translateY(-100%)';
    } else {
        // Scrolling up
        navbar.style.transform = 'translateY(0)';
    }
    
    lastScroll = currentScroll;
});

// Intersection Observer for fade-in animations
const observerOptions = {
    root: null,
    threshold: 0.1,
    rootMargin: '0px'
};

const observer = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate-fadeIn');
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Observe all feature cards
document.querySelectorAll('.feature-card').forEach(card => {
    observer.observe(card);
});

// Add loading state to buttons when clicked
document.querySelectorAll('a').forEach(button => {
    button.addEventListener('click', function(e) {
        if (this.href && !this.href.startsWith('#')) {
            this.classList.add('loading');
        }
    });
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check for redirect from 404 page
    const redirect = sessionStorage.redirect;
    if (redirect && redirect !== location.href) {
        history.replaceState(null, null, redirect);
        delete sessionStorage.redirect;
    }
    
    // Add initial animations
    document.querySelector('.hero-title').classList.add('animate-fadeIn');
    document.querySelector('.hero-subtitle').classList.add('animate-fadeIn');
}); 