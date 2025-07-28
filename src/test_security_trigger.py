"""
Test file to trigger security suggestions and auto task creation
This file contains intentional security issues for testing SupervisorAgent
"""

# Hardcoded secrets - should trigger high priority security suggestion
DATABASE_PASSWORD = "supersecret123"
API_KEY = "sk-1234567890abcdef"
SECRET_TOKEN = "my-secret-token-value"

def unsafe_sql_query(user_input):
    """Function with SQL injection vulnerability"""
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    # This should trigger SQL injection risk detection
    cursor.execute(query)
    return cursor.fetchall()

def another_unsafe_function(data):
    """Another function with security issues"""
    password = "hardcoded_admin_password"
    return f"User data: {data}, Password: {password}"

def complex_function_that_should_trigger_refactor():
    """This is an overly complex function that should trigger refactor suggestion"""
    result = []
    for i in range(100):
        if i % 2 == 0:
            for j in range(10):
                if j % 3 == 0:
                    for k in range(5):
                        if k % 2 == 1:
                            temp_value = i * j * k
                            if temp_value > 50:
                                result.append(temp_value)
                            else:
                                result.append(temp_value * 2)
                        else:
                            temp_value = i + j + k
                            if temp_value < 20:
                                result.append(temp_value)
                            else:
                                result.append(temp_value / 2)
                else:
                    for k in range(3):
                        temp = i * j + k
                        result.append(temp)
            # More complex logic here
            for j in range(5):
                temp = i * 2
                result.append(temp)
        else:
            for j in range(8):
                temp = i + j
                result.append(temp)
    
    # Process results
    final_result = []
    for item in result:
        if item > 100:
            final_result.append(item * 0.5)
        elif item > 50:
            final_result.append(item * 0.75)
        else:
            final_result.append(item * 1.25)
    
    return final_result

# Functions without docstrings to trigger documentation suggestion
def undocumented_function_one():
    return "no docs"

def undocumented_function_two():
    return "also no docs"

def undocumented_function_three():
    return "still no docs"

def undocumented_function_four():
    return "you guessed it"

def undocumented_function_five():
    return "no documentation here either"

def undocumented_function_six():
    return "documentation gap example"
