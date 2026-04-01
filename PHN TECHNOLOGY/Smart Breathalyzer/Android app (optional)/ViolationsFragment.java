package com.asvi.breathalyzer;

import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.fragment.app.Fragment;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.google.firebase.database.DataSnapshot;
import com.google.firebase.database.DatabaseError;
import com.google.firebase.database.FirebaseDatabase;
import com.google.firebase.database.ValueEventListener;

import java.util.ArrayList;
import java.util.List;

public class ViolationsFragment extends Fragment {

    private RecyclerView recyclerView;
    private RecordAdapter adapter;
    private List<Record> violationList = new ArrayList<>();

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View view = inflater.inflate(R.layout.fragment_violations, container, false);

        recyclerView = view.findViewById(R.id.violationsRecyclerView);
        recyclerView.setLayoutManager(new LinearLayoutManager(getContext()));
        adapter = new RecordAdapter(violationList);
        recyclerView.setAdapter(adapter);

        loadViolations();
        return view;
    }


    // pull only entries where the person has been caught 3 or more times
    private void loadViolations() {
        FirebaseDatabase.getInstance().getReference("violations")
            .addValueEventListener(new ValueEventListener() {
                @Override
                public void onDataChange(@NonNull DataSnapshot snapshot) {
                    violationList.clear();
                    for (DataSnapshot entry : snapshot.getChildren()) {
                        Record record = entry.getValue(Record.class);
                        if (record != null && record.getDrunkCount() >= 3) {
                            violationList.add(record);
                        }
                    }
                    adapter.notifyDataSetChanged();
                }

                @Override
                public void onCancelled(@NonNull DatabaseError error) {
                    Toast.makeText(getContext(), "failed to load violations", Toast.LENGTH_SHORT).show();
                }
            });
    }
}
