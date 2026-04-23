// Simple form validation and confirmation
const form = document.getElementById('serviceForm');
if(form){
    form.addEventListener('submit', function(e){
        e.preventDefault();
        const name = document.getElementById('name').value;
        const service = document.getElementById('service').value;
        document.getElementById('formMessage').textContent = `Thank you ${name}! Your booking for ${service} has been received.`;
        form.reset();
    });
}
