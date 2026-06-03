// SHIFTLY Dynamic UI Engine

document.addEventListener("DOMContentLoaded", () => {
    // 1. Scroll-sensitive Navigation Headers
    const navbar = document.querySelector(".navbar");
    window.addEventListener("scroll", () => {
        if (window.scrollY > 50) {
            navbar.classList.add("navbar-scrolled");
        } else {
            navbar.classList.remove("navbar-scrolled");
        }
    });

    // 2. Tinder-style Swipe Simulator
    const swipeDeck = [
        {
            title: "Specialty Barista",
            business: "Blue Bottle Coffee",
            rate: "$24.50",
            location: "SOMA, San Francisco",
            time: "Fri, 8 AM - 4 PM",
            image: "https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?auto=format&fit=crop&w=400&q=80",
            badge: "Top Rated"
        },
        {
            title: "Boutique Retail Assistant",
            business: "Everlane",
            rate: "$21.00",
            location: "Hayes Valley, SF",
            time: "Sat, 10 AM - 6 PM",
            image: "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=400&q=80",
            badge: "Urgent"
        },
        {
            title: "Event Hospitality Host",
            business: "Palace Hotel",
            rate: "$26.00",
            location: "Downtown, SF",
            time: "Thu, 5 PM - 11 PM",
            image: "https://images.unsplash.com/photo-1511795409834-ef04bbd61622?auto=format&fit=crop&w=400&q=80",
            badge: "Premium Pay"
        }
    ];

    let currentCardIndex = 0;
    const cardContainer = document.getElementById("sim-card-container");
    const nopeBtn = document.getElementById("sim-btn-nope");
    const likeBtn = document.getElementById("sim-btn-like");
    const matchModal = document.getElementById("sim-match-modal");
    const closeMatchBtn = document.getElementById("close-match-modal");

    function renderCard() {
        if (!cardContainer) return;
        cardContainer.innerHTML = "";
        
        // Render 2 cards to simulate stack depth
        for (let i = 1; i >= 0; i--) {
            const index = (currentCardIndex + i) % swipeDeck.length;
            const data = swipeDeck[index];
            
            const card = document.createElement("div");
            card.className = `swipe-card ${i === 0 ? "active-card" : "background-card"}`;
            if (i === 1) {
                card.style.transform = "scale(0.95) translateY(10px)";
                card.style.zIndex = "1";
                card.style.opacity = "0.7";
            } else {
                card.style.zIndex = "2";
            }
            
            card.innerHTML = `
                <div class="swipe-card-image" style="background-image: url('${data.image}')">
                    <span class="swipe-card-badge badge-nope">NOPE</span>
                    <span class="swipe-card-badge badge-like">LIKE</span>
                </div>
                <div class="swipe-card-body">
                    <div>
                        <div class="d-flex justify-content-between align-items-start mb-1">
                            <h4 class="mb-0 fs-5">${data.title}</h4>
                            <span class="badge bg-danger bg-opacity-10 text-danger rounded-pill px-2 py-1 fs-6">${data.badge}</span>
                        </div>
                        <p class="text-muted mb-2">${data.business} • ${data.location}</p>
                        <small class="d-block text-white mb-2"><i class="bi bi-clock"></i> ${data.time}</small>
                    </div>
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="fs-4 fw-bold text-gradient-coral">${data.rate}<small class="fs-6 fw-normal text-muted">/hr</small></span>
                        <button class="btn btn-premium-outline btn-sm py-1 px-3">Details</button>
                    </div>
                </div>
            `;
            cardContainer.appendChild(card);
        }
    }

    function handleSwipe(direction) {
        const activeCard = document.querySelector(".active-card");
        const nextCard = document.querySelector(".background-card");
        if (!activeCard) return;

        if (direction === "right") {
            activeCard.classList.add("sim-swipe-right");
        } else {
            activeCard.classList.add("sim-swipe-left");
        }

        // Lift background card
        if (nextCard) {
            setTimeout(() => {
                nextCard.style.transform = "scale(1) translateY(0)";
                nextCard.style.opacity = "1";
                nextCard.style.zIndex = "2";
                nextCard.classList.remove("background-card");
                nextCard.classList.add("active-card");
            }, 100);
        }

        // Cycle stack index
        setTimeout(() => {
            currentCardIndex = (currentCardIndex + 1) % swipeDeck.length;
            renderCard();
            
            // Random Match Simulation on "Like" (Swipe Right)
            if (direction === "right" && Math.random() > 0.4) {
                showMatchModal();
            }
        }, 400);
    }

    function showMatchModal() {
        if (!matchModal) return;
        matchModal.classList.add("show-modal");
        
        // Add dynamic audio effect (optional/virtual)
        const matchCard = swipeDeck[currentCardIndex];
        document.getElementById("match-job-title").innerText = matchCard.title;
        document.getElementById("match-company").innerText = matchCard.business;
    }

    if (nopeBtn) nopeBtn.addEventListener("click", () => handleSwipe("left"));
    if (likeBtn) likeBtn.addEventListener("click", () => handleSwipe("right"));
    
    if (closeMatchBtn) {
        closeMatchBtn.addEventListener("click", () => {
            matchModal.classList.remove("show-modal");
        });
    }

    // Initialize Card Render
    renderCard();
});
