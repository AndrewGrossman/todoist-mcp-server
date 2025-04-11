#!/usr/bin/env python3

from mcp.server.fastmcp import FastMCP
from todoist_api_python.api import TodoistAPI
import os
import logging
from typing import Optional, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("todoist-mcp-server")

# Check for API token
TODOIST_API_TOKEN = os.getenv("TODOIST_API_TOKEN")
if not TODOIST_API_TOKEN:
    logger.error("TODOIST_API_TOKEN environment variable is required")
    exit(1)

# Initialize Todoist client
try:
    todoist_client = TodoistAPI(TODOIST_API_TOKEN)
    logger.info("Todoist API client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Todoist client: {e}")
    exit(1)

# Create an MCP server
mcp = FastMCP("Todoist MCP Server")

@mcp.tool()
def todoist_create_task(
    content: str,
    description: Optional[str] = None,
    due_string: Optional[str] = None,
    priority: Optional[int] = None
) -> str:
    """Create a new task in Todoist with optional description, due date, and priority

    Args:
        content: The content/title of the task
        description: Detailed description of the task (optional)
        due_string: Natural language due date like 'tomorrow', 'next Monday', 'Jan 23' (optional)
        priority: Task priority from 1 (normal) to 4 (urgent) (optional)
    """
    try:
        logger.info(f"Creating task: {content}")

        # Create task parameters
        task_params = {
            "content": content
        }

        # Add optional parameters if provided
        if description:
            task_params["description"] = description
        if due_string:
            task_params["due_string"] = due_string
        if priority and 1 <= priority <= 4:
            task_params["priority"] = priority

        # Create the task
        task = todoist_client.add_task(**task_params)

        # Format response
        response = f"Task created:\nTitle: {task.content}"
        if hasattr(task, 'description') and task.description:
            response += f"\nDescription: {task.description}"
        if hasattr(task, 'due') and task.due:
            response += f"\nDue: {task.due.string}"
        if hasattr(task, 'priority') and task.priority:
            response += f"\nPriority: {task.priority}"

        logger.info(f"Task created successfully: {task.id}")
        return response
    except Exception as error:
        logger.error(f"Error creating task: {error}")
        return f"Error creating task: {str(error)}"

@mcp.tool()
def todoist_get_tasks(
    project_id: Optional[str] = None,
    filter: Optional[str] = None,
    priority: Optional[int] = None,
    limit: int = 10
) -> str:
    """Get a list of tasks from Todoist with various filters

    Args:
        project_id: Filter tasks by project ID (optional)
        filter: Natural language filter like 'today', 'tomorrow', 'next week', 'priority 1', 'overdue' (optional)
        priority: Filter by priority level (1-4) (optional)
        limit: Maximum number of tasks to return (optional)
    """
    try:
        logger.info(f"Getting tasks with filter: {filter}, project_id: {project_id}, priority: {priority}, limit: {limit}")

        # Create API request parameters
        params: Dict[str, Any] = {}
        if project_id:
            params["project_id"] = project_id
        if filter:
            params["filter"] = filter

        # Get tasks
        tasks = todoist_client.get_tasks(**params)

        # Apply additional filters that aren't supported directly by the API
        if priority and 1 <= priority <= 4:
            tasks = [task for task in tasks if task.priority == priority]

        # Apply limit
        if limit and limit > 0:
            tasks = tasks[:limit]

        # Format response
        if not tasks:
            logger.info("No tasks found matching the criteria")
            return "No tasks found matching the criteria"

        task_list = []
        for task in tasks:
            task_text = f"- {task.content}"
            if hasattr(task, 'description') and task.description:
                task_text += f"\n  Description: {task.description}"
            if hasattr(task, 'due') and task.due:
                task_text += f"\n  Due: {task.due.string}"
            if hasattr(task, 'priority') and task.priority:
                task_text += f"\n  Priority: {task.priority}"
            task_list.append(task_text)

        logger.info(f"Retrieved {len(tasks)} tasks")
        return "\n\n".join(task_list)
    except Exception as error:
        logger.error(f"Error getting tasks: {error}")
        return f"Error getting tasks: {str(error)}"

@mcp.tool()
def todoist_update_task(
    task_name: str,
    content: Optional[str] = None,
    description: Optional[str] = None,
    due_string: Optional[str] = None,
    priority: Optional[int] = None
) -> str:
    """Update an existing task in Todoist by searching for it by name and then updating it

    Args:
        task_name: Name/content of the task to search for and update
        content: New content/title for the task (optional)
        description: New description for the task (optional)
        due_string: New due date in natural language like 'tomorrow', 'next Monday' (optional)
        priority: New priority level from 1 (normal) to 4 (urgent) (optional)
    """
    try:
        logger.info(f"Updating task matching: {task_name}")

        # First, search for the task
        tasks = todoist_client.get_tasks()
        matching_task = None

        for task in tasks:
            if task_name.lower() in task.content.lower():
                matching_task = task
                break

        if not matching_task:
            logger.warning(f"No task found matching: {task_name}")
            return f"Could not find a task matching \"{task_name}\""

        # Build update data
        update_data = {}
        if content:
            update_data["content"] = content
        if description:
            update_data["description"] = description
        if due_string:
            update_data["due_string"] = due_string
        if priority and 1 <= priority <= 4:
            update_data["priority"] = priority

        # Update the task
        is_success = todoist_client.update_task(task_id=matching_task.id, **update_data)

        if is_success:
            logger.info(f"Task updated successfully: {matching_task.id}")

            # Format response
            response = f"Task \"{matching_task.content}\" updated:"
            if content:
                response += f"\nNew Title: {content}"
            if description:
                response += f"\nNew Description: {description}"
            if due_string:
                response += f"\nNew Due Date: derived from '{due_string}'"
            if priority:
                response += f"\nNew Priority: {priority}"

            return response
        else:
            logger.warning(f"Task update failed for task ID: {matching_task.id}")
            return "Task update failed"
    except Exception as error:
        logger.error(f"Error updating task: {error}")
        return f"Error updating task: {str(error)}"

@mcp.tool()
def todoist_delete_task(task_name: str) -> str:
    """Delete a task from Todoist by searching for it by name

    Args:
        task_name: Name/content of the task to search for and delete
    """
    try:
        logger.info(f"Deleting task matching: {task_name}")

        # First, search for the task
        tasks = todoist_client.get_tasks()
        matching_task = None

        for task in tasks:
            if task_name.lower() in task.content.lower():
                matching_task = task
                break

        if not matching_task:
            logger.warning(f"No task found matching: {task_name}")
            return f"Could not find a task matching \"{task_name}\""

        # Delete the task
        is_success = todoist_client.delete_task(task_id=matching_task.id)

        if is_success:
            logger.info(f"Task deleted successfully: {matching_task.id}")
            return f"Successfully deleted task: \"{matching_task.content}\""
        else:
            logger.warning(f"Task deletion failed for task ID: {matching_task.id}")
            return "Task deletion failed"
    except Exception as error:
        logger.error(f"Error deleting task: {error}")
        return f"Error deleting task: {str(error)}"

@mcp.tool()
def todoist_complete_task(task_name: str) -> str:
    """Mark a task as complete by searching for it by name

    Args:
        task_name: Name/content of the task to search for and complete
    """
    try:
        logger.info(f"Completing task matching: {task_name}")

        # First, search for the task
        tasks = todoist_client.get_tasks()
        matching_task = None

        for task in tasks:
            if task_name.lower() in task.content.lower():
                matching_task = task
                break

        if not matching_task:
            logger.warning(f"No task found matching: {task_name}")
            return f"Could not find a task matching \"{task_name}\""

        # Complete the task
        is_success = todoist_client.close_task(task_id=matching_task.id)

        if is_success:
            logger.info(f"Task completed successfully: {matching_task.id}")
            return f"Successfully completed task: \"{matching_task.content}\""
        else:
            logger.warning(f"Task completion failed for task ID: {matching_task.id}")
            return "Task completion failed"
    except Exception as error:
        logger.error(f"Error completing task: {error}")
        return f"Error completing task: {str(error)}"

# Run the server
if __name__ == "__main__":
    logger.info("Starting Todoist MCP Server")
    # Run with stdio transport
    mcp.run(transport='stdio')
