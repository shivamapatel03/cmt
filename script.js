// Smooth scrolling for navigation links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Loading screen animation
window.addEventListener('load', () => {
    setTimeout(() => {
        document.body.style.opacity = '1';
    }, 1500);
});

// 3D Model Interaction
class Model3DController {
    constructor() {
        this.robotModel = document.querySelector('.robot-model');
        this.tagModel = document.querySelector('.tag-model');
        this.isAnimating = false;
        this.rotationX = 0;
        this.rotationY = 0;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Robot model interaction
        this.robotModel.addEventListener('mousemove', (e) => this.handleMouseMove(e, this.robotModel));
        this.robotModel.addEventListener('mouseleave', () => this.handleMouseLeave(this.robotModel));
        this.robotModel.addEventListener('click', () => this.handleClick(this.robotModel));

        // TAG model interaction
        this.tagModel.addEventListener('mousemove', (e) => this.handleMouseMove(e, this.tagModel));
        this.tagModel.addEventListener('mouseleave', () => this.handleMouseLeave(this.tagModel));
        this.tagModel.addEventListener('click', () => this.handleClick(this.tagModel));
    }

    handleMouseMove(e, element) {
        if (this.isAnimating) return;

        const rect = element.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        this.rotationY = ((x / rect.width) - 0.5) * 30;
        this.rotationX = ((y / rect.height) - 0.5) * 30;

        element.style.transform = `
            rotateX(${-this.rotationX}deg) 
            rotateY(${this.rotationY}deg)
            scale(1.1)
        `;
    }

    handleMouseLeave(element) {
        if (this.isAnimating) return;
        element.style.transform = 'rotateX(0) rotateY(0) scale(1)';
    }

    handleClick(element) {
        if (this.isAnimating) return;
        this.isAnimating = true;

        element.style.transform = 'rotateY(360deg) scale(1.2)';
        setTimeout(() => {
            element.style.transform = 'rotateY(0) scale(1)';
            this.isAnimating = false;
        }, 1000);
    }
}

// Feature Cards Animation
class FeatureCardsController {
    constructor() {
        this.cards = document.querySelectorAll('.feature-card');
        this.initializeObserver();
    }

    initializeObserver() {
        const options = {
            root: null,
            threshold: 0.2
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('card-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, options);

        this.cards.forEach(card => observer.observe(card));
    }
}

// Vision Cards Animation
class VisionCardsController {
    constructor() {
        this.cards = document.querySelectorAll('.vision-card');
        this.initializeObserver();
    }

    initializeObserver() {
        const options = {
            root: null,
            threshold: 0.2
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.transform = 'translateX(0)';
                    entry.target.style.opacity = '1';
                    observer.unobserve(entry.target);
                }
            });
        }, options);

        this.cards.forEach(card => observer.observe(card));
    }
}

// Team Members Animation
class TeamMembersController {
    constructor() {
        this.members = document.querySelectorAll('.team-member');
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        this.members.forEach(member => {
            member.addEventListener('mouseenter', () => this.handleHover(member, true));
            member.addEventListener('mouseleave', () => this.handleHover(member, false));
        });
    }

    handleHover(member, isHovering) {
        const image = member.querySelector('.member-image');
        const name = member.querySelector('h3');
        const education = member.querySelector('.education');

        if (isHovering) {
            image.style.transform = 'translateZ(60px) scale(1.1)';
            name.style.transform = 'translateZ(40px)';
            education.style.transform = 'translateZ(20px)';
        } else {
            image.style.transform = 'translateZ(40px) scale(1)';
            name.style.transform = 'translateZ(30px)';
            education.style.transform = 'translateZ(15px)';
        }
    }
}

// Initialize all controllers
document.addEventListener('DOMContentLoaded', () => {
    new Model3DController();
    new FeatureCardsController();
    new VisionCardsController();
    new TeamMembersController();
}); 