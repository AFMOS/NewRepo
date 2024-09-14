import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Set the page configuration to wide mode
st.set_page_config(layout="wide")

# Load the data
try:
    data = pd.read_csv('sales_data.csv')  # Replace with the path to your CSV file
except FileNotFoundError:
    st.error("The file 'sales_data.csv' was not found.")
    st.stop()
except pd.errors.EmptyDataError:
    st.error("The file 'sales_data.csv' is empty.")
    st.stop()
except pd.errors.ParserError:
    st.error("Error parsing 'sales_data.csv'. Please check the file format.")
    st.stop()

# Month order for sorting
month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Define quarter mapping
quarter_map = {
    'Q1': ["Jan", "Feb", "Mar"],
    'Q2': ["Apr", "May", "Jun"],
    'Q3': ["Jul", "Aug", "Sep"],
    'Q4': ["Oct", "Nov", "Dec"]
}

def update_dashboard(selected_areas, selected_month, selected_quarter, 
                      selected_customer_categories, selected_salesmen, selected_item_categories,
                      selected_customer_names):
    # Filter data based on selections
    filtered_data = data
    if selected_areas and selected_areas != "None":
        filtered_data = filtered_data[filtered_data['area'] == selected_areas]
    if selected_month and selected_month != "None":
        filtered_data = filtered_data[filtered_data['month'] == selected_month]
    if selected_quarter and selected_quarter != "None":
        months = quarter_map[selected_quarter]
        filtered_data = filtered_data[filtered_data['month'].isin(months)]
    if selected_customer_categories and selected_customer_categories != "None":
        filtered_data = filtered_data[filtered_data['customer_category'] == selected_customer_categories]
    if selected_salesmen and selected_salesmen != "None":
        filtered_data = filtered_data[filtered_data['salesman'] == selected_salesmen]
    if selected_item_categories and selected_item_categories != "None":
        filtered_data = filtered_data[filtered_data['item_category'] == selected_item_categories]
    if selected_customer_names and selected_customer_names != "None":
        filtered_data = filtered_data[filtered_data['customer_name'] == selected_customer_names]

    # Calculate summary statistics
    total_sales = filtered_data['total'].sum()
    customer_count = filtered_data['customer_code'].nunique()
    total_weight = filtered_data['weight'].sum()
    
    total_customers = filtered_data['customer_code'].nunique()
    if total_customers > 0:
        Cash_count = filtered_data[filtered_data['payment_type'] == 'Cash']['customer_code'].nunique()
        Credit_count = filtered_data[filtered_data['payment_type'] == 'Credit']['customer_code'].nunique()
        
        Cash_percentage = Cash_count / total_customers
        Credit_percentage = Credit_count / total_customers
    else:
        Cash_count = Credit_count = 0
        Cash_percentage = Credit_percentage = 0

    # Create charts using Plotly
    # Sales by Area Pie Chart
    sales_by_area = filtered_data.groupby('area')['total'].sum().reset_index()
    fig_area = px.pie(sales_by_area, values='total', names='area', title='Sales by Area')

    # Sales by Month Bar Chart
    sales_by_month = filtered_data.groupby('month')['total'].sum().reset_index()
    sales_by_month['month'] = pd.Categorical(sales_by_month['month'], categories=month_order, ordered=True)
    sales_by_month = sales_by_month.sort_values('month')
    fig_month = px.bar(sales_by_month, y='month', x='total', title='Sales by Month', text='total', orientation='h')
    fig_month.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig_month.update_layout(
        xaxis_title='Total Sales',
        yaxis_title='Month',
        title='Sales by Month'
    )

    # Sales by Quarter Bar Chart
    sales_by_quarter = filtered_data.copy()
    sales_by_quarter['quarter'] = sales_by_quarter['month'].apply(lambda x: next((q for q, months in quarter_map.items() if x in months), None))
    sales_by_quarter = sales_by_quarter.groupby('quarter')['total'].sum().reset_index()
    fig_quarter = px.bar(sales_by_quarter, x='quarter', y='total', title='Sales by Quarter', text='total')
    fig_quarter.update_traces(texttemplate='%{text:.2s}', textposition='outside')
    fig_quarter.update_layout(
        xaxis_title='Quarter',
        yaxis_title='Total Sales',
        title='Sales by Quarter'
    )
    
    # Sales by Salesman and Area Vertical Bar Chart
    sales_by_salesman_area = filtered_data.groupby(['area', 'salesman'])['total'].sum().reset_index()
    
    # Create the vertical bar chart
    fig_salesman = go.Figure()
    
    areas = sales_by_salesman_area['area'].unique()
    if len(areas) > 0:
        for area in areas:
            subset = sales_by_salesman_area[sales_by_salesman_area['area'] == area]
            fig_salesman.add_trace(go.Bar(
                x=subset['salesman'],
                y=subset['total'],
                name=area,
                text=subset['total'],
                texttemplate='%{text:.2s}',
                textposition='outside'
            ))
    
    fig_salesman.update_layout(
        title='Sales by Salesman and Area',
        xaxis_title='Salesman',
        yaxis_title='Total Sales',
        barmode='group',  # Display bars side by side
        xaxis=dict(title='Salesman', tickangle=-45),  # Rotate x-axis labels for readability
        legend_title='Area'  # Title for the legend
    )
    
    # Ensure all traces are visible by default
    fig_salesman.update_traces(visible=True)
    
    # Generate Heatmap
    pivot_table = filtered_data.pivot_table(index='item_category', columns='month', values='weight', aggfunc='sum')
    
    # Ensure columns are sorted by month order
    pivot_table = pivot_table.reindex(columns=month_order)
    
    # Sort rows by total weight in descending order
    pivot_table['total'] = pivot_table.sum(axis=1)
    pivot_table = pivot_table.sort_values('total', ascending=True)
    pivot_table = pivot_table.drop('total', axis=1)
    
    # Round the values and replace NaN with empty string
    rounded_values = pivot_table.round(0).fillna('')
    text_values = rounded_values.astype(str)
    text_values = text_values.replace('0.0', '', regex=False)
    
    # Create heatmap using go.Heatmap
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot_table.values,
        x=pivot_table.columns,
        y=pivot_table.index,
        colorscale='matter',
        hoverongaps=False,
        text=text_values,
        texttemplate="%{text}",
        showscale=False  # Hide the color scale (legend)
    ))
    
    fig_heatmap.update_layout(
        title='Item CTG heatmap',
        xaxis_title='',
        yaxis_title='',
        height=800,  # Fixed height
        xaxis=dict(side='top')  # Move x-axis labels to the top
    )

    return (total_sales, customer_count, total_weight, Cash_count, Credit_count,
            Cash_percentage, Credit_percentage, fig_area, fig_month, fig_quarter, fig_salesman, fig_heatmap)

# Streamlit app
st.markdown("""<h1 style="text-align: center;">📊 Sales Dashboard</h1>""", unsafe_allow_html=True)

# Filters aligned to the right
st.sidebar.header('Filters')
selected_areas = st.sidebar.selectbox('Select Area', options=['None'] + list(data['area'].unique()))
selected_month = st.sidebar.selectbox('Select Month', options=['None'] + list(data['month'].unique()))
selected_quarter = st.sidebar.selectbox('Select Quarter', options=['None'] + list(quarter_map.keys()))
selected_customer_categories = st.sidebar.selectbox('Select Customer Category', options=['None'] + list(data['customer_category'].unique()))
selected_salesmen = st.sidebar.selectbox('Select Salesman', options=['None'] + list(data['salesman'].unique()))
selected_item_categories = st.sidebar.selectbox('Select Item Category', options=['None'] + list(data['item_category'].unique()))
selected_customer_names = st.sidebar.selectbox('Select Customer Name', options=['None'] + list(data['customer_name'].unique()))

# Update dashboard based on selections
(total_sales, customer_count, total_weight, Cash_count, Credit_count,
 Cash_percentage, Credit_percentage, fig_area, fig_month, fig_quarter, fig_salesman, fig_heatmap) = update_dashboard(
    selected_areas, selected_month, selected_quarter, 
    selected_customer_categories, selected_salesmen, selected_item_categories,
    selected_customer_names
)

# Layout with columns for summary statistics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 12px; text-align: center;">
        <h4 style="margin: 0; font-size: 14px;">Total Sales</h4>
        <h2 style="margin: 0; font-size: 16px;">SAR {total_sales:,.0f}</h2>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 12px; text-align: center;">
        <h4 style="margin: 0; font-size: 14px;">Customer Count</h4>
        <h2 style="margin: 0; font-size: 16px;">{customer_count:,}</h2>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 12px; text-align: center;">
        <h4 style="margin: 0; font-size: 14px;">Total Weight</h4>
        <h2 style="margin: 0; font-size: 16px;">{total_weight:,.0f} kg</h2>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; font-size: 12px; text-align: center;">
        <h4 style="margin: 0; font-size: 14px;">Payment Type</h4>
        <h2 style="margin: 0; font-size: 16px;">Cash: {Cash_count:,} ({Cash_percentage:.1%})</h2>
        <h2 style="margin: 0; font-size: 16px;">Credit: {Credit_count:,} ({Credit_percentage:.1%})</h2>
    </div>
    """, unsafe_allow_html=True)

# Display charts side by side and centered
st.subheader('Sales Visualizations')
col1, col2, col3, col4 = st.columns([3, 3, 3, 3])  # Adjust column widths to be equal

with col1:
    st.plotly_chart(fig_area, use_container_width=True)

with col2:
    st.plotly_chart(fig_month, use_container_width=True)

with col3:
    st.plotly_chart(fig_quarter, use_container_width=True)

with col4:
    st.plotly_chart(fig_salesman, use_container_width=True)

# Add a new section for the heatmap
st.subheader('Item CTG heatmap')
st.plotly_chart(fig_heatmap, use_container_width=True)
