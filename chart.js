// Floor counts
venues_by_floor = [
    {"floor": floor, "count": count}
    for floor, count in db.session.query(Venue.venueLevel, func.count())
    .group_by(Venue.venueLevel)
    .order_by(Venue.venueLevel)
    .all()
]

// --- Pie Chart: Venue by Floow
const floorLabels = [{{ venues_by_floor | map(attribute='floor') | map('tojson') | join(', ') }}];
const floorData = [{{ venues_by_floor | map(attribute='count') | join(', ') }}];

const ctxVenueFloor = document.getElementById('venueFloorPieChart').getContext('2d');
new Chart(ctxVenueFloor, {
    type: 'pie',
    data: {
        labels: floorLabels,
        datasets: [{
            label: "Venues by Floor",
            data: floorData,
            backgroundColor: [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                '#9966FF', '#FF9F40'
            ]
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { position: 'bottom' },
            tooltip: {
                callbacks: {
                    label: function (context) {
                        let data = context.dataset.data;
                        let sum = data.reduce((a, b) => a + b, 0);
                        let value = context.parsed;
                        let percentage = ((value / sum) * 100).toFixed(1) + "%";
                        return context.label + ": " + value + " (" + percentage + ")";
                    }
                }
            }
        }
    }
});



// --- Pie Chart: Courses by Department ---
new Chart(document.getElementById('courseDeptPieChart'), {
    type: 'pie',
    data: {
        labels: {{ (courses_by_department | map(attribute='department') | list) | tojson | safe }},
        datasets: [{
            data: {{ (courses_by_department | map(attribute='count') | list) | tojson | safe }},
            backgroundColor: [
                '#FF6384','#36A2EB','#FFCE56',
                '#4BC0C0','#9966FF','#FF9F40',
                '#C9CBCF','#8BC34A','#E91E63'
            ],
            borderWidth: 1
        }]
    },
    options: {
        responsive: true,
        plugins: {
            legend: { position: 'right' },
            tooltip: {
                callbacks: {
                    label: ({ dataset, parsed, label }) => {
                        const sum = dataset.data.reduce((a, b) => a + b, 0);
                        return `${label}: ${parsed} (${(parsed/sum*100).toFixed(1)}%)`;
                    }
                }
            }
        }
    }
});

// --- Line Chart: Courses by Department ---
const ctx = document.getElementById('courseDeptLineChart');
if (ctx) {
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: {{ (courses_by_department | map(attribute='department') | list) | tojson | safe }},
            datasets: [{
                label: "Courses by Department",
                data: {{ (courses_by_department | map(attribute='count') | list) | tojson | safe }},
                borderColor: '#36A2EB',
                backgroundColor: '#36A2EB',
                tension: 0.3,
                fill: false,
                borderWidth: 2,
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: {
                    callbacks: {
                        label: ({ dataset, parsed, label }) => {
                            const sum = dataset.data.reduce((a, b) => a + Number(b), 0);
                            const val = Number(parsed);
                            return `${label}: ${val} (${(val / sum * 100).toFixed(1)}%)`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}