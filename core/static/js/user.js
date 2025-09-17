// Variables
const createBtn = document.getElementById('create-btn');
const educationModal = document.getElementById('education-modal');
const closeBtn = document.getElementById('close-btn');

// Event Listeners
if (createBtn && educationModal && closeBtn) {
    // Show modal
    createBtn.addEventListener('click', function() {
        educationModal.style.display = 'block';
        educationModal.classList.add('show');
    });

    // Hide modal
    closeBtn.addEventListener('click', function() {
        educationModal.style.display = 'none';
        educationModal.classList.remove('show');
    });

    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === educationModal) {
            educationModal.style.display = 'none';
            educationModal.classList.remove('show');
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    // Handle add experience form submission
    document.getElementById('experienceForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        
        fetch("{% url 'add_experience' %}", {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': '{{ csrf_token }}'
            }
        })
        .then(response => response.json())
        .then(data => {
            if(data.success) {
                location.reload();
            }
        });
    });

    // Handle edit experience buttons
    document.querySelectorAll('.edit-experience-btn').forEach(button => {
        button.addEventListener('click', function() {
            const expId = this.getAttribute('data-exp-id');
            fetch(`/get_experience/${expId}/`)  // Dynamically build the URL
                .then(response => response.json())
                .then(data => {
                    // Populate the modal with experience data
                    document.getElementById('edit_exp_id').value = data.id;
                    document.getElementById('edit_title').value = data.title;
                    document.getElementById('edit_company').value = data.company;
                    document.getElementById('edit_start_date').value = data.start_date;
                    document.getElementById('edit_end_date').value = data.end_date || '';
                    document.getElementById('edit_description').value = data.description;
                    const modal = new bootstrap.Modal(document.getElementById('editExperienceModal'));
                    modal.show();
                })
                .catch(error => console.error('Error fetching experience:', error));
        });
    });

    // Handle edit experience form submission
    document.getElementById('editExperienceForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        
        fetch("{% url 'update_experience' %}", {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': '{{ csrf_token }}'
            }
        })
        .then(response => response.json())
        .then(data => {
            if(data.success) {
                location.reload();
            }
        });
    });
    
    // Handle education form submission
    document.getElementById('educationForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        
        fetch("{% url 'add_education' %}", {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': '{{ csrf_token }}'
            }
        })
        .then(response => response.json())
        .then(data => {
            if(data.success) {
                location.reload();
            }
        });
    });
});