// JavaScript to ensure asterisk shows on assigned_doctor field - AGGRESSIVE VERSION
(function() {
    'use strict';
    
    function addAsterisk() {
        console.log('Patient Admin JS: Starting asterisk addition...');
        
        // Method 1: Find by exact ID
        var label = document.querySelector('label[for="id_assigned_doctor"]');
        
        if (label) {
            console.log('Found label:', label.textContent);
            
            // Remove existing asterisk if any
            var existingAsterisk = label.querySelector('.required-asterisk');
            if (existingAsterisk) {
                existingAsterisk.remove();
            }
            
            // Check if asterisk already in text
            if (!label.textContent.includes('*')) {
                // Create asterisk element
                var asterisk = document.createElement('span');
                asterisk.className = 'required-asterisk';
                asterisk.textContent = ' *';
                asterisk.style.color = '#ff0000';
                asterisk.style.fontWeight = 'bold';
                asterisk.style.fontSize = '16px';
                asterisk.style.marginLeft = '5px';
                asterisk.style.display = 'inline-block';
                label.appendChild(asterisk);
                
                console.log('✅ Added asterisk to assigned_doctor label');
            } else {
                console.log('⚠️ Asterisk already in label text');
            }
        } else {
            console.log('❌ Label not found');
        }
        
        // Method 2: Find by class
        var formRow = document.querySelector('.form-row.field-assigned_doctor');
        if (formRow) {
            formRow.classList.add('required');
            console.log('✅ Added required class to form row');
        }
        
        // Method 3: Add to all labels in Required Information section
        var requiredFieldset = document.querySelector('fieldset.module');
        if (requiredFieldset) {
            var h2 = requiredFieldset.querySelector('h2');
            if (h2 && h2.textContent.includes('Required Information')) {
                var labels = requiredFieldset.querySelectorAll('.form-row label');
                labels.forEach(function(lbl) {
                    if (!lbl.textContent.includes('*')) {
                        var ast = document.createElement('span');
                        ast.className = 'required-asterisk';
                        ast.textContent = ' *';
                        ast.style.color = '#ff0000';
                        ast.style.fontWeight = 'bold';
                        ast.style.fontSize = '14px';
                        ast.style.marginLeft = '3px';
                        lbl.appendChild(ast);
                    }
                });
                console.log('✅ Added asterisks to all required fields');
            }
        }
    }
    
    // Try multiple times to ensure it works
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addAsterisk);
    } else {
        addAsterisk();
    }
    
    // Also try after a short delay
    setTimeout(addAsterisk, 100);
    setTimeout(addAsterisk, 500);
    setTimeout(addAsterisk, 1000);
    
})();
