function openPanel() {
    document.getElementById('panel').classList.add('active');
    document.getElementById('calendar').style.width = '45%';
}

function closePanel() {
    document.getElementById('panel').classList.remove('active');
    document.getElementById('calendar').style.width = '70%';
}