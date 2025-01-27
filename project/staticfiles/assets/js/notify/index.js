'use strict';
var notify = $.notify('<i class="fa fa-bell-o"></i><strong>Ma\'lumotlar</strong> yuklanmoqda...', {
    type: 'theme',
    allow_dismiss: true,
    delay: 1000,
    showProgressbar: true,
    timer: 300
});

setTimeout(function() {
    notify.update('message', '<i class="fa fa-bell-o"></i><strong>Ma\'lumotlar</strong> muvaffaqiyatli yuklandi!');
}, 1000);
