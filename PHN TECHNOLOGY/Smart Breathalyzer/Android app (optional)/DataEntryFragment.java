package com.asvi.breathalyzer;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.fragment.app.Fragment;

import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.DatabaseReference;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public class DataEntryFragment extends Fragment {

    private EditText licenseField, nameField, surnameField, vehicleField, emailField, concentrationField;
    private Button fetchButton, submitButton;

    private DatabaseReference db;

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_data_entry, container, false);

        licenseField       = view.findViewById(R.id.licenseField);
        nameField          = view.findViewById(R.id.nameField);
        surnameField       = view.findViewById(R.id.surnameField);
        vehicleField       = view.findViewById(R.id.vehicleField);
        emailField         = view.findViewById(R.id.emailField);
        concentrationField = view.findViewById(R.id.concentrationField);
        fetchButton        = view.findViewById(R.id.fetchButton);
        submitButton       = view.findViewById(R.id.submitButton);

        db = FirebaseDatabase.getInstance().getReference();

        // fetch existing person details using the license number
        fetchButton.setOnClickListener(v -> fetchPersonDetails());

        // submit the current reading as a new violation entry
        submitButton.setOnClickListener(v -> submitEntry());

        // listen for concentration readings pushed by the ESP32 via Firebase
        listenForBreathalyzerReading();

        return view;
    }


    // watch for new readings the ESP32 writes to Firebase in real time
    private void listenForBreathalyzerReading() {
        db.child("latest_reading").addValueEventListener(new ValueEventListener() {
            @Override
            public void onDataChange(@NonNull DataSnapshot snapshot) {
                if (snapshot.exists()) {
                    String concentration = snapshot.child("concentration").getValue(String.class);
                    if (concentration != null) {
                        concentrationField.setText(concentration);
                    }
                }
            }

            @Override
            public void onCancelled(@NonNull DatabaseError error) {
                Toast.makeText(getContext(), "failed to read sensor data", Toast.LENGTH_SHORT).show();
            }
        });
    }


    // look up previously saved details for this license number
    private void fetchPersonDetails() {
        String license = licenseField.getText().toString().trim();
        if (license.isEmpty()) {
            Toast.makeText(getContext(), "enter a license number first", Toast.LENGTH_SHORT).show();
            return;
        }

        db.child("people").child(license).addListenerForSingleValueEvent(new ValueEventListener() {
            @Override
            public void onDataChange(@NonNull DataSnapshot snapshot) {
                if (snapshot.exists()) {
                    nameField.setText(snapshot.child("name").getValue(String.class));
                    surnameField.setText(snapshot.child("surname").getValue(String.class));
                    vehicleField.setText(snapshot.child("vehicleNumber").getValue(String.class));
                    emailField.setText(snapshot.child("email").getValue(String.class));
                    Toast.makeText(getContext(), "details fetched", Toast.LENGTH_SHORT).show();
                } else {
                    Toast.makeText(getContext(), "no existing record for this license", Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onCancelled(@NonNull DatabaseError error) {
                Toast.makeText(getContext(), "fetch failed", Toast.LENGTH_SHORT).show();
            }
        });
    }


    // save a new violation entry and update the person's drunk count
    private void submitEntry() {
        String license       = licenseField.getText().toString().trim();
        String name          = nameField.getText().toString().trim();
        String surname       = surnameField.getText().toString().trim();
        String vehicleNumber = vehicleField.getText().toString().trim();
        String email         = emailField.getText().toString().trim();
        String concentration = concentrationField.getText().toString().trim();

        if (license.isEmpty() || name.isEmpty() || concentration.isEmpty()) {
            Toast.makeText(getContext(), "fill in all required fields", Toast.LENGTH_SHORT).show();
            return;
        }

        String timestamp = new SimpleDateFormat("EEE MMM dd HH:mm:ss z yyyy", Locale.getDefault())
                .format(new Date());

        // get the current drunk count and increment it
        db.child("people").child(license).addListenerForSingleValueEvent(new ValueEventListener() {
            @Override
            public void onDataChange(@NonNull DataSnapshot snapshot) {
                int drunkCount = 0;
                if (snapshot.exists() && snapshot.child("drunkCount").getValue() != null) {
                    drunkCount = snapshot.child("drunkCount").getValue(Integer.class);
                }
                int newCount = drunkCount + 1;

                Record record = new Record(
                    license, name, surname, vehicleNumber, email,
                    "fetching location...", timestamp,
                    Integer.parseInt(concentration), newCount
                );

                // save under people (latest details) and records (full history)
                db.child("people").child(license).setValue(record);
                db.child("records").push().setValue(record);

                // if this person has hit 3 strikes, add them to violations
                if (newCount >= 3) {
                    db.child("violations").child(license).setValue(record);
                }

                sendViolationEmail(email, name, newCount, concentration);
                Toast.makeText(getContext(), "entry submitted — strike " + newCount, Toast.LENGTH_SHORT).show();
                clearFields();
            }

            @Override
            public void onCancelled(@NonNull DatabaseError error) {
                Toast.makeText(getContext(), "submit failed", Toast.LENGTH_SHORT).show();
            }
        });
    }


    // send the appropriate email depending on how many strikes this person has
    private void sendViolationEmail(String email, String name, int strikes, String concentration) {
        new Thread(() -> {
            try {
                java.util.Properties props = new java.util.Properties();
                props.put("mail.smtp.auth",            "true");
                props.put("mail.smtp.starttls.enable", "true");
                props.put("mail.smtp.host",            "smtp.gmail.com");
                props.put("mail.smtp.port",            "587");

                javax.mail.Session session = javax.mail.Session.getInstance(props,
                    new javax.mail.Authenticator() {
                        protected javax.mail.PasswordAuthentication getPasswordAuthentication() {
                            return new javax.mail.PasswordAuthentication(
                                "your_email@gmail.com", "your_app_password"
                            );
                        }
                    }
                );

                String subject, body;
                if (strikes == 1) {
                    subject = "drunk driving warning — first offense";
                    body    = "dear " + name + ", you have been caught drink driving. BAC: " + concentration + ". this is your first warning.";
                } else if (strikes == 2) {
                    subject = "drunk driving warning — second offense";
                    body    = "dear " + name + ", you have been caught drink driving again. BAC: " + concentration + ". this is your final warning.";
                } else {
                    subject = "court summons — third drunk driving offense";
                    body    = "dear " + name + ", you have been caught drink driving 3 or more times. BAC: " + concentration + ". a court summons has been issued.";
                }

                javax.mail.internet.MimeMessage message = new javax.mail.internet.MimeMessage(session);
                message.setFrom(new javax.mail.internet.InternetAddress("your_email@gmail.com"));
                message.setRecipients(javax.mail.Message.RecipientType.TO,
                    javax.mail.internet.InternetAddress.parse(email));
                message.setSubject(subject);
                message.setText(body);
                javax.mail.Transport.send(message);

            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }


    private void clearFields() {
        licenseField.setText("");
        nameField.setText("");
        surnameField.setText("");
        vehicleField.setText("");
        emailField.setText("");
        concentrationField.setText("");
    }
}
